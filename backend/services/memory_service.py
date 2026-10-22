import ast
import json
import re
from typing import List, Dict, Any, Optional
from memory.chroma_store import (
    get_all_memories,
    search_related_memories,
    get_collection_name_for_workspace,
    get_chroma_client,
    list_workspaces
)

def parse_memory_doc(doc_text: str) -> Dict[str, str]:
    sections = {}
    summary_idx = doc_text.find("SUMMARY:")
    critique_idx = doc_text.find("CRITIQUE:")
    research_idx = doc_text.find("FULL RESEARCH:")

    if summary_idx != -1 and critique_idx != -1 and research_idx != -1:
        sections['topic'] = doc_text[:summary_idx].replace("TOPIC:", "").strip()
        sections['summary'] = doc_text[summary_idx:critique_idx].replace("SUMMARY:", "").strip()
        sections['critique'] = doc_text[critique_idx:research_idx].replace("CRITIQUE:", "").strip()
        sections['full_research'] = doc_text[research_idx:].replace("FULL RESEARCH:", "").strip()
    else:
        sections['raw'] = doc_text
        sections['summary'] = doc_text[:500]
        sections['critique'] = ""
        sections['full_research'] = doc_text

    return sections

def parse_critique_dict(critique_str: str) -> Any:
    if not critique_str:
        return None
    critique_str = critique_str.strip()
    try:
        return ast.literal_eval(critique_str)
    except Exception:
        pass
    try:
        return json.loads(critique_str)
    except Exception:
        pass
    try:
        match = re.search(r'\{.*\}', critique_str, re.DOTALL)
        if match:
            return ast.literal_eval(match.group(0))
    except Exception:
        pass
    try:
        match = re.search(r'\{.*\}', critique_str, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return critique_str

class MemoryService:
    def list_memories(self, query: Optional[str] = None, workspace: str = "default") -> List[Dict[str, Any]]:
        if query and query.strip():
            raw_memories = search_related_memories(query_text=query.strip(), n_results=10, workspace=workspace)
        else:
            raw_memories = get_all_memories(workspace=workspace)

        items = []
        for mem in raw_memories:
            doc_id = mem.get("id")
            doc_text = mem.get("document", "")
            metadata = mem.get("metadata", {})
            parsed = parse_memory_doc(doc_text)
            crit_parsed = parse_critique_dict(parsed.get("critique", ""))

            items.append({
                "id": doc_id,
                "topic": metadata.get("topic", parsed.get("topic", "Untitled Research")),
                "summary": parsed.get("summary", ""),
                "critique": crit_parsed,
                "full_research": parsed.get("full_research", doc_text),
                "metadata": metadata,
                "created_at": metadata.get("timestamp")
            })

        return items

    def get_memory(self, doc_id: str, workspace: str = "default") -> Optional[Dict[str, Any]]:
        all_mems = self.list_memories(workspace=workspace)
        for item in all_mems:
            if item["id"] == doc_id:
                return item
        return None

    def delete_memory(self, doc_id: str, workspace: str = "default") -> bool:
        try:
            client = get_chroma_client()
            col_name = get_collection_name_for_workspace(workspace)
            col = client.get_collection(name=col_name)
            col.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"[MemoryService Error] Failed to delete memory {doc_id}: {e}")
            return False

    def get_workspaces(self) -> List[str]:
        return list_workspaces()

memory_service = MemoryService()
