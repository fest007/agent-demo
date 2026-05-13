import React from "react";
import { BulbOutlined } from "@ant-design/icons";
import type { ThoughtStep } from "@/types";
import styles from "./ThoughtBlock.module.css";

export const ThoughtBlock: React.FC<{ thoughts: ThoughtStep[] }> = ({ thoughts }) => (
  <div className={styles.panel}>
    <div className={styles.header}>
      <BulbOutlined />
      <span>处理状态</span>
    </div>
    <div className={styles.list}>
      {thoughts.map((thought, index) => (
        <div className={styles.item} key={`${thought.timestamp.getTime()}-${index}`}>
          <span className={styles.dot} />
          <span>{thought.text}</span>
        </div>
      ))}
    </div>
  </div>
);
