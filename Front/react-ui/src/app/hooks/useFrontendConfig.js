import { useCallback, useEffect, useRef, useState } from "react";
import { fetchFrontendConfig, isClientDebugEnabled } from "../utils/api";

export function useFrontendConfig(apiBase) {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [heroWelcomeText, setHeroWelcomeText] = useState("");
  const [configReady, setConfigReady] = useState(false);
  const requestIdRef = useRef(0);

  const loadFrontendConfig = useCallback(async ({ markPending = false } = {}) => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    if (markPending) {
      setConfigReady(false);
    }

    try {
      const config = await fetchFrontendConfig(apiBase);
      if (requestIdRef.current !== requestId) return;
      if (isClientDebugEnabled() && config.debug) {
        console.log("[xiexin-debug] frontend-config", config.debug);
      }
      const nextModels = Array.isArray(config.availableModels) ? config.availableModels : [];
      const nextSelectedModel = config.defaultModel || nextModels[0] || "";
      const nextHeroWelcomeText = String(config.heroWelcomeText || "").trim();
      setModels(nextModels);
      setSelectedModel(nextSelectedModel);
      setHeroWelcomeText(nextHeroWelcomeText);
      setConfigReady(true);
    } catch {
      if (requestIdRef.current !== requestId) return;
      setModels([]);
      setSelectedModel("");
      setHeroWelcomeText("");
      setConfigReady(true);
    }
  }, [apiBase]);

  useEffect(() => {
    void loadFrontendConfig();
  }, [loadFrontendConfig]);

  const refreshFrontendConfig = useCallback(async () => {
    await loadFrontendConfig({ markPending: true });
  }, [loadFrontendConfig]);

  return {
    models,
    selectedModel,
    setSelectedModel,
    heroWelcomeText,
    configReady,
    refreshFrontendConfig,
  };
}
