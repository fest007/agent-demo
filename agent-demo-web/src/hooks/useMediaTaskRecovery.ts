import { useEffect } from "react";
import { listMediaTasks } from "@/api/media";
import { mediaTaskPoller } from "@/utils/MediaTaskPoller";

export function useMediaTaskRecovery() {
  useEffect(() => {
    let disposed = false;
    listMediaTasks("pending,running,succeeded,failed")
      .then(({ tasks }) => {
        if (disposed) return;
        const recent = tasks.slice(0, 20);
        recent.forEach((task) => mediaTaskPoller.watch(task));
      })
      .catch(() => {});
    return () => {
      disposed = true;
    };
  }, []);
}
