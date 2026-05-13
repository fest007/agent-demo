import React from "react";
import { FileSearchOutlined } from "@ant-design/icons";
import { useAppStore } from "@/stores/appStore";
import type { KnowledgeCitation } from "@/types";
import styles from "./CitationBlock.module.css";

export const CitationBlock: React.FC<{ citations: KnowledgeCitation[] }> = ({ citations }) => {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);
  const setKnowledgeFocus = useAppStore((s) => s.setKnowledgeFocus);

  const openCitation = (source: string, chunkId: string) => {
    setKnowledgeFocus({ source, chunkId });
    setCurrentPage("knowledge");
  };

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <FileSearchOutlined />
        <span>引用来源</span>
      </div>
      <div className={styles.list}>
        {citations.map((citation, index) => (
          <button
            className={styles.item}
            key={`${citation.chunk_id}-${index}`}
            onClick={() => openCitation(citation.source, citation.chunk_id)}
          >
            <span className={styles.index}>[{index + 1}]</span>
            <span className={styles.main}>
              <span className={styles.title}>{citation.title || citation.source}</span>
              <span className={styles.excerpt}>{citation.excerpt}</span>
            </span>
            <span className={styles.chunk}>片段 {citation.chunk_index}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
