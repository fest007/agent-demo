import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./AnswerBlock.module.css";

export const AnswerBlock: React.FC<{
  content: string;
  isThinking: boolean;
  isRegenerating: boolean;
}> = ({ content, isThinking, isRegenerating }) => (
  <div className={styles.bubble}>
    {isThinking ? (
      <div className={styles.waiting}>
        <div className={styles.loadingDots}>
          <div className={styles.loadingDot} />
          <div className={styles.loadingDot} />
          <div className={styles.loadingDot} />
        </div>
        <span>等待正文输出</span>
      </div>
    ) : (
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    )}
    {isRegenerating && <span className={styles.cursor} />}
  </div>
);
