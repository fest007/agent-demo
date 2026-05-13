import React from "react";
import type { MediaTask } from "@/types";
import { ImageGenerationBlock } from "./ImageGenerationBlock";
import { VideoGenerationBlock } from "./VideoGenerationBlock";
import styles from "./MediaBlock.module.css";

export const MediaBlock: React.FC<{ tasks: MediaTask[] }> = ({ tasks }) => {
  if (!tasks.length) return null;

  return (
    <div className={styles.stack}>
      {tasks.map((task) =>
        task.task_type === "video" ? (
          <VideoGenerationBlock key={task.id} task={task} />
        ) : (
          <ImageGenerationBlock key={task.id} task={task} />
        ),
      )}
    </div>
  );
};
