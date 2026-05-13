"use client";

import { useEffect, useRef, useState } from "react";

export function usePyodide() {
  const [isReady, setIsReady] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    // Initialize Web Worker
    workerRef.current = new Worker(new URL("./pyodide.worker.ts", import.meta.url), {
      type: "classic",
    });

    const id = Date.now().toString();

    workerRef.current.onmessage = (e) => {
      if (e.data.id === id && e.data.type === "INIT_SUCCESS") {
        setIsReady(true);
      }
    };

    workerRef.current.postMessage({ type: "INIT", id });

    return () => {
      workerRef.current?.terminate();
    };
  }, []);

  const renderAudio = async (crdJson: any): Promise<Float32Array> => {
    if (!workerRef.current || !isReady) throw new Error("Worker not ready");
    setIsRendering(true);

    return new Promise((resolve, reject) => {
      const id = Date.now().toString() + Math.random();

      const handler = (e: MessageEvent) => {
        if (e.data.id === id) {
          workerRef.current?.removeEventListener("message", handler);
          setIsRendering(false);
          
          if (e.data.type === "RENDER_SUCCESS") {
            resolve(e.data.data as Float32Array);
          } else {
            reject(new Error(e.data.error));
          }
        }
      };

      workerRef.current?.addEventListener("message", handler);
      workerRef.current?.postMessage({ type: "RENDER", payload: crdJson, id });
    });
  };

  return { isReady, isRendering, renderAudio };
}
