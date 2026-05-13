import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Divider,
  Form,
  Input,
  Progress,
  Select,
  Slider,
  Space,
  Statistic,
  Switch,
  Typography,
  message,
} from "antd";
import { ReloadOutlined, SettingOutlined } from "@ant-design/icons";
import {
  fetchRemoteModels,
  listModelProviders,
  queryQuota,
  type ModelProviderInfo,
  type RemoteModelInfo,
  type QuotaResponse,
} from "@/api/settings";
import { useAppStore } from "@/stores/appStore";
import styles from "./Settings.module.css";

const CUSTOM_PROVIDER_ID = "custom";

function isVolcengineChatModel(modelId: string): boolean {
  const lowered = modelId.toLowerCase();
  const nonChatKeywords = [
    "seedream",
    "seedance",
    "seed3d",
    "hitem3d",
    "hyper3d",
    "tts",
    "podcast",
    "voice-design",
  ];
  return !nonChatKeywords.some((keyword) => lowered.includes(keyword));
}

function isImageModel(modelId: string): boolean {
  return modelId.toLowerCase().includes("seedream");
}

function isVideoModel(modelId: string): boolean {
  return modelId.toLowerCase().includes("seedance");
}

const Settings: React.FC = () => {
  const modelSelection = useAppStore((state) => state.modelSelection);
  const setModelSelection = useAppStore((state) => state.setModelSelection);
  const markdownTypingSpeed = useAppStore((state) => state.markdownTypingSpeed);
  const setMarkdownTypingSpeed = useAppStore((state) => state.setMarkdownTypingSpeed);
  const [providers, setProviders] = useState<ModelProviderInfo[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState(modelSelection.providerId || "mimo");
  const [selectedModelId, setSelectedModelId] = useState(modelSelection.modelId || "");
  const [selectedImageModelId, setSelectedImageModelId] = useState(
    modelSelection.imageModelId || "doubao-seedream-5-0-260128",
  );
  const [selectedVideoModelId, setSelectedVideoModelId] = useState(
    modelSelection.videoModelId || "doubao-seedance-1-5-pro-251215",
  );
  const [selectedKeyId, setSelectedKeyId] = useState(modelSelection.apiKeyId || "default");
  const [customBaseUrl, setCustomBaseUrl] = useState(modelSelection.customBaseUrl || "");
  const [customApiKey, setCustomApiKey] = useState(modelSelection.customApiKey || "");
  const [remoteModels, setRemoteModels] = useState<RemoteModelInfo[]>([]);
  const [modelsMessage, setModelsMessage] = useState("");
  const [modelsStatus, setModelsStatus] = useState<"idle" | "ok" | "empty" | "error">("idle");
  const [quota, setQuota] = useState<QuotaResponse | null>(null);
  const [providersLoading, setProvidersLoading] = useState(false);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [quotaLoading, setQuotaLoading] = useState(false);

  const selectedProvider = useMemo(
    () => providers.find((item) => item.id === selectedProviderId),
    [providers, selectedProviderId],
  );
  const isCustomProvider = selectedProviderId === CUSTOM_PROVIDER_ID;

  const selectedKey = useMemo(
    () => selectedProvider?.keys.find((item) => item.id === selectedKeyId),
    [selectedProvider, selectedKeyId],
  );

  const providerBaseUrl = isCustomProvider ? customBaseUrl : customBaseUrl || selectedProvider?.base_url || "";
  const currentKeyLabel = customApiKey.trim()
    ? "页面自定义 Key"
    : selectedKey?.label || (isCustomProvider ? "页面自定义 Key" : "当前 Key");
  const currentKeyMasked = customApiKey.trim()
    ? `${customApiKey.trim().slice(0, 6)}...${customApiKey.trim().slice(-4)}`
    : selectedKey?.masked || "";
  const canQueryQuota = Boolean(
    providerBaseUrl.trim() && (customApiKey.trim() || (!isCustomProvider && selectedKeyId)),
  );

  const formatNumber = (value?: number | null) => {
    if (value === null || value === undefined) return "-";
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);
  };

  const clearRemoteModels = () => {
    setRemoteModels([]);
    setModelsMessage("");
    setModelsStatus("idle");
  };

  const saveSelection = () => {
    if (!selectedProviderId) {
      message.warning("请先选择模型供应商");
      return;
    }
    if (!selectedModelId.trim()) {
      message.warning("请填写模型 ID 或推理接入点 ID");
      return;
    }
    if (isCustomProvider && !customBaseUrl.trim()) {
      message.warning("选择其他供应商时需要填写 Base URL");
      return;
    }
    if (isCustomProvider && !customApiKey.trim()) {
      message.warning("选择其他供应商时需要填写 API Key");
      return;
    }
    if (selectedProviderId === "volcengine" && !isVolcengineChatModel(selectedModelId.trim())) {
      message.warning("该火山方舟模型不是聊天对话模型，请选择文本/代码对话模型");
      return;
    }
    if (selectedProviderId === "volcengine" && selectedImageModelId.trim() && !isImageModel(selectedImageModelId.trim())) {
      message.warning("图片生成模型应选择 Seedream / 图像生成模型");
      return;
    }
    if (selectedProviderId === "volcengine" && selectedVideoModelId.trim() && !isVideoModel(selectedVideoModelId.trim())) {
      message.warning("视频生成模型应选择 Seedance / 视频生成模型");
      return;
    }
    setModelSelection({
      providerId: selectedProviderId,
      modelId: selectedModelId.trim(),
      imageModelId: selectedImageModelId.trim() || undefined,
      videoModelId: selectedVideoModelId.trim() || undefined,
      apiKeyId: selectedKeyId,
      customBaseUrl: providerBaseUrl.trim() || undefined,
      customApiKey: customApiKey.trim() || undefined,
    });
    message.success("模型配置已保存，后续对话会使用当前配置");
  };

  const loadQuota = async (
    providerId = selectedProviderId,
    keyId = selectedKeyId,
    baseUrlOverride?: string,
    apiKeyOverride?: string,
  ) => {
    const providerForQuota = providers.find((item) => item.id === providerId);
    const apiKey = apiKeyOverride ?? customApiKey.trim();
    const baseUrl = baseUrlOverride ?? (
      providerId === CUSTOM_PROVIDER_ID
        ? customBaseUrl.trim()
        : customBaseUrl.trim() || providerForQuota?.base_url || ""
    );
    if (!providerId || !baseUrl || (!apiKey && !keyId)) {
      setQuota({
        provider: providerId || CUSTOM_PROVIDER_ID,
        key_id: keyId || "custom",
        key_label: currentKeyLabel,
        supported: false,
        status: "error",
        unit: "credit",
        message: "请先配置 Base URL 和 API Key，再查询额度。",
      });
      return;
    }
    setQuotaLoading(true);
    try {
      const data = await queryQuota({
        provider: providerId,
        keyId: keyId || "custom",
        customBaseUrl: baseUrl,
        customApiKey: apiKey || undefined,
      });
      setQuota(data);
    } catch (error) {
      setQuota({
        provider: providerId,
        key_id: keyId,
        key_label: currentKeyLabel,
        supported: false,
        status: "error",
        unit: "credit",
        message: error instanceof Error ? error.message : "额度查询失败",
      });
    } finally {
      setQuotaLoading(false);
    }
  };

  const loadRemoteModels = async () => {
    if (!providerBaseUrl.trim()) {
      message.warning("请先填写 Base URL");
      return;
    }
    if (isCustomProvider && !customApiKey.trim()) {
      message.warning("请先填写 API Key");
      return;
    }
    if (!isCustomProvider && !customApiKey.trim() && !selectedKeyId) {
      message.warning("请先选择后端已配置的 API Key，或填写 API Key 覆盖");
      return;
    }

    setModelsLoading(true);
    try {
      const data = await fetchRemoteModels({
        provider: selectedProviderId,
        keyId: selectedKeyId,
        customBaseUrl: providerBaseUrl.trim(),
        customApiKey: customApiKey.trim() || undefined,
      });
      setRemoteModels(data.models || []);
      const chatCount = (data.models || []).filter((item) => item.chat_supported).length;
      setModelsMessage(
        data.status === "ok"
          ? `${data.message} 其中 ${chatCount} 个可用于当前聊天对话。`
          : data.message,
      );
      setModelsStatus(data.status === "ok" ? "ok" : data.status === "empty" ? "empty" : "error");
      if (data.status === "ok") {
        message.success(data.message || "模型列表获取成功");
      } else {
        message.warning(data.message || "未获取到模型列表，可手动输入模型 ID");
      }
    } catch (error) {
      setRemoteModels([]);
      setModelsStatus("error");
      setModelsMessage(error instanceof Error ? error.message : "获取模型列表失败，可手动输入模型 ID");
      message.warning("获取模型列表失败，可手动输入模型 ID");
    } finally {
      setModelsLoading(false);
    }
  };

  const applyProviderDefaults = (items: ModelProviderInfo[]) => {
    if (modelSelection.providerId === CUSTOM_PROVIDER_ID) {
      setSelectedProviderId(CUSTOM_PROVIDER_ID);
      setSelectedModelId(modelSelection.modelId || "");
      setSelectedImageModelId(modelSelection.imageModelId || "");
      setSelectedVideoModelId(modelSelection.videoModelId || "");
      setSelectedKeyId("custom");
      setCustomBaseUrl(modelSelection.customBaseUrl || "");
      setCustomApiKey(modelSelection.customApiKey || "");
      clearRemoteModels();
      return;
    }

    const provider =
      items.find((item) => item.id === modelSelection.providerId) ||
      items.find((item) => item.keys.length > 0 && item.models.length > 0) ||
      items[0];
    if (!provider) {
      setSelectedProviderId(CUSTOM_PROVIDER_ID);
      setSelectedModelId(modelSelection.modelId || "");
      setSelectedImageModelId(modelSelection.imageModelId || "");
      setSelectedVideoModelId(modelSelection.videoModelId || "");
      setSelectedKeyId("custom");
      return;
    }

    const model =
      provider.models.find((item) => item.id === modelSelection.modelId) ||
      provider.models.find((item) => item.id === provider.default_model) ||
      provider.models[0];
    const key =
      provider.keys.find((item) => item.id === modelSelection.apiKeyId) ||
      provider.keys[0];

    const nextProviderId = provider.id;
    const nextModelId = modelSelection.modelId || model?.id || provider.default_model || "";
    const nextKeyId = key?.id || "";
    setSelectedProviderId(nextProviderId);
    setSelectedModelId(nextModelId);
    setSelectedImageModelId(modelSelection.imageModelId || "doubao-seedream-5-0-260128");
    setSelectedVideoModelId(modelSelection.videoModelId || "doubao-seedance-1-5-pro-251215");
    setSelectedKeyId(nextKeyId);
    setCustomBaseUrl(modelSelection.customBaseUrl || "");
    setCustomApiKey(modelSelection.customApiKey || "");
    clearRemoteModels();
    if (nextKeyId) loadQuota(nextProviderId, nextKeyId, provider.base_url, "");
  };

  const loadProviders = async () => {
    setProvidersLoading(true);
    try {
      const data = await listModelProviders();
      setProviders(data);
      applyProviderDefaults(data);
    } finally {
      setProvidersLoading(false);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleProviderChange = (providerId: string) => {
    if (providerId === CUSTOM_PROVIDER_ID) {
      setSelectedProviderId(providerId);
      setSelectedKeyId("custom");
      setQuota(null);
      clearRemoteModels();
      return;
    }
    const provider = providers.find((item) => item.id === providerId);
    const model =
      provider?.models.find((item) => item.id === provider.default_model) ||
      provider?.models[0];
    const key = provider?.keys[0];
    setSelectedProviderId(providerId);
    setSelectedModelId(model?.id || "");
    setSelectedImageModelId(providerId === "volcengine" ? "doubao-seedream-5-0-260128" : "");
    setSelectedVideoModelId(providerId === "volcengine" ? "doubao-seedance-1-5-pro-251215" : "");
    setSelectedKeyId(key?.id || "");
    setCustomBaseUrl("");
    setCustomApiKey("");
    setQuota(null);
    clearRemoteModels();
    if (key?.id) loadQuota(providerId, key.id, provider?.base_url || "", "");
  };

  const handleKeyChange = (keyId: string) => {
    setSelectedKeyId(keyId);
    setCustomApiKey("");
    clearRemoteModels();
    const provider = providers.find((item) => item.id === selectedProviderId);
    loadQuota(selectedProviderId, keyId, provider?.base_url || "", "");
  };

  const percentRemaining = quota?.percent_remaining ?? 0;
  const progressStatus = quota?.status === "ok" && quota.supported ? "normal" : "exception";

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <div className={styles.header}>
          <div className={styles.titleRow}>
            <div className={styles.titleIcon}>
              <SettingOutlined />
            </div>
            <span className={styles.title}>设置</span>
          </div>
          <p className={styles.description}>配置模型、语音和界面选项</p>
        </div>

        <Card className={styles.card}>
          <Form layout="vertical">
            <div className={styles.modelSection}>
              <div className={styles.quotaHeader}>
                <div>
                  <div className={styles.quotaTitle}>模型供应商</div>
                  <div className={styles.quotaDesc}>保存后，新的对话请求会使用当前模型配置</div>
                </div>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadProviders}
                  loading={providersLoading}
                  className={styles.refreshButton}
                >
                  刷新配置
                </Button>
              </div>

              <Alert
                type="info"
                showIcon
                className={styles.compatAlert}
                message="当前仅支持 OpenAI-compatible Chat Completions 返回格式"
                description="供应商需要兼容 /chat/completions 的消息、工具调用和流式 chunk 格式。"
              />

              <Form.Item label="供应商">
                <Select
                  value={selectedProviderId}
                  loading={providersLoading}
                  onChange={handleProviderChange}
                  options={[
                    ...providers.map((item) => ({
                      value: item.id,
                      label: item.label,
                    })),
                    { value: CUSTOM_PROVIDER_ID, label: "其他" },
                  ]}
                  placeholder="暂无可用供应商"
                />
              </Form.Item>

              <Form.Item label={isCustomProvider ? "Base URL" : "Base URL 覆盖"}>
                <Input
                  value={providerBaseUrl}
                  onChange={(event) => {
                    setCustomBaseUrl(event.target.value);
                    clearRemoteModels();
                  }}
                  placeholder={selectedProvider?.base_url || "https://example.com/v1"}
                />
              </Form.Item>

              <Form.Item label="对话模型 ID / 推理接入点 ID">
                <Space.Compact className={styles.modelPicker}>
                  <Input
                    value={selectedModelId}
                    onChange={(event) => setSelectedModelId(event.target.value)}
                    placeholder={isCustomProvider ? "model-id" : selectedProvider?.default_model || "请输入模型 ID"}
                  />
                  <Button onClick={loadRemoteModels} loading={modelsLoading}>
                    获取模型列表
                  </Button>
                </Space.Compact>
              </Form.Item>

              <Form.Item label="图片生成模型 ID">
                <Input
                  value={selectedImageModelId}
                  onChange={(event) => setSelectedImageModelId(event.target.value)}
                  placeholder="doubao-seedream-5-0-260128"
                />
              </Form.Item>

              <Form.Item label="视频生成模型 ID">
                <Input
                  value={selectedVideoModelId}
                  onChange={(event) => setSelectedVideoModelId(event.target.value)}
                  placeholder="doubao-seedance-1-5-pro-251215"
                />
              </Form.Item>

              {(remoteModels.length > 0 || modelsMessage) && (
                <div className={styles.modelListPanel}>
                  {modelsMessage && (
                    <Alert
                      type={modelsStatus === "ok" ? "success" : "warning"}
                      showIcon
                      className={styles.modelListAlert}
                      message={modelsMessage}
                    />
                  )}
                  {remoteModels.length > 0 && (
                    <div className={styles.modelList}>
                      {remoteModels.map((model) => (
                        <div
                          key={model.id}
                          role="button"
                          tabIndex={0}
                          className={`${styles.modelListItem} ${
                            selectedModelId === model.id ? styles.modelListItemActive : ""
                          } ${!model.chat_supported ? styles.modelListItemDisabled : ""}`}
                          title={model.note}
                          onClick={() => {
                            if (!model.chat_supported) {
                              message.warning(model.note || "该模型不适用于聊天对话");
                              return;
                            }
                            setSelectedModelId(model.id);
                          }}
                        >
                          <span className={styles.modelListLabel}>
                            {model.label || model.id}
                            <em className={model.chat_supported ? styles.modelTagChat : styles.modelTagMuted}>
                              {model.capability || (model.chat_supported ? "文本对话" : "非聊天")}
                            </em>
                          </span>
                          <Typography.Text type="secondary">
                            {model.id}
                            {!model.chat_supported ? ` · ${model.note}` : ""}
                          </Typography.Text>
                          <span className={styles.modelAssignActions}>
                            <Button
                              size="small"
                              disabled={!model.chat_supported}
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedModelId(model.id);
                              }}
                            >
                              对话
                            </Button>
                            <Button
                              size="small"
                              disabled={!model.image_supported}
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedImageModelId(model.id);
                              }}
                            >
                              图片
                            </Button>
                            <Button
                              size="small"
                              disabled={!model.video_supported}
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedVideoModelId(model.id);
                              }}
                            >
                              视频
                            </Button>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {!isCustomProvider && selectedProvider?.keys.length ? (
                <Form.Item label="后端已配置 API Key">
                  <Select
                    value={selectedKeyId}
                    onChange={handleKeyChange}
                    options={selectedProvider.keys.map((item) => ({
                      value: item.id,
                      label: `${item.label} (${item.masked})`,
                    }))}
                  />
                </Form.Item>
              ) : null}

              <Form.Item label={isCustomProvider ? "API Key" : "API Key 覆盖"}>
                <Input.Password
                  value={customApiKey}
                  onChange={(event) => {
                    setCustomApiKey(event.target.value);
                    clearRemoteModels();
                  }}
                  placeholder={isCustomProvider ? "请输入 API Key" : "留空则使用后端已配置的 Key"}
                  autoComplete="off"
                />
              </Form.Item>

              <div className={styles.modelActions}>
                <Typography.Text type="secondary" className={styles.providerMeta}>
                  {isCustomProvider ? "其他 OpenAI-compatible 供应商" : selectedProvider?.label || "未选择供应商"}
                  {providerBaseUrl ? ` · ${providerBaseUrl}` : ""}
                </Typography.Text>
                <Button type="primary" onClick={saveSelection} className={styles.saveInlineButton}>
                  保存模型配置
                </Button>
              </div>
            </div>

            <Divider className={styles.divider} />

            <Form.Item label="TTS 引擎">
              <Select
                defaultValue="edge-tts"
                options={[
                  { value: "mimo-tts", label: "MiMo TTS" },
                  { value: "edge-tts", label: "Edge TTS" },
                ]}
              />
            </Form.Item>
            <Form.Item label="语音">
              <Select
                defaultValue="zh-CN-XiaoxiaoNeural"
                options={[
                  { value: "zh-CN-XiaoxiaoNeural", label: "晓晓 (女声)" },
                  { value: "zh-CN-YunxiNeural", label: "云希 (男声)" },
                ]}
              />
            </Form.Item>
            <Divider className={styles.divider} />

            <div className={styles.quotaSection}>
              <div className={styles.quotaHeader}>
                <div>
                  <div className={styles.quotaTitle}>API Key 额度</div>
                  <div className={styles.quotaDesc}>按当前供应商、Base URL 和 API Key 查询；不支持时会显示明确提示</div>
                </div>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => loadQuota()}
                  loading={quotaLoading}
                  disabled={!canQueryQuota}
                  className={styles.refreshButton}
                >
                  刷新
                </Button>
              </div>

              <div className={styles.quotaPanel}>
                <div className={styles.quotaMeta}>
                  <span>{selectedProvider?.label || (isCustomProvider ? "其他" : quota?.provider) || "当前供应商"}</span>
                  <Typography.Text type="secondary">
                    {quota?.key_label || currentKeyLabel}
                    {currentKeyMasked ? ` ${currentKeyMasked}` : ""}
                  </Typography.Text>
                </div>
                <Progress
                  percent={Number(percentRemaining.toFixed(1))}
                  status={progressStatus}
                  strokeColor={progressStatus === "normal" ? "#10b981" : "#ef4444"}
                />
                <Space className={styles.quotaStats} size="large">
                  <Statistic
                    title="剩余额度"
                    value={formatNumber(quota?.remaining)}
                    suffix={quota?.unit}
                    loading={quotaLoading}
                  />
                  <Statistic
                    title="已使用"
                    value={formatNumber(quota?.used)}
                    suffix={quota?.unit}
                    loading={quotaLoading}
                  />
                  <Statistic
                    title="总额度"
                    value={formatNumber(quota?.total)}
                    suffix={quota?.unit}
                    loading={quotaLoading}
                  />
                </Space>
                {quota && quota.status !== "ok" && (
                  <Alert
                    type="warning"
                    showIcon
                    className={styles.quotaAlert}
                    message={quota.status === "unsupported" ? "额度查询暂不支持" : "额度查询不可用"}
                    description={quota.message}
                  />
                )}
                {quota && quota.status === "ok" && (
                  <Typography.Text type="secondary" className={styles.quotaMessage}>
                    {quota.message}
                  </Typography.Text>
                )}
              </div>
            </div>

            <Divider className={styles.divider} />
            <Form.Item label="自动语音播放" className={styles.switchItem}>
              <Switch />
            </Form.Item>
            <Form.Item label="显示情绪标识" className={styles.switchItem}>
              <Switch defaultChecked />
            </Form.Item>
            <Form.Item label="显示工具调用" className={styles.toolSwitchItem}>
              <Switch defaultChecked />
            </Form.Item>

            <Divider className={styles.divider} />
            <Form.Item
              label={`Markdown 打字速度：${markdownTypingSpeed} 字/秒`}
              tooltip="控制流式回答进入 Markdown 的渲染速度。调高更快，调低更柔和。"
            >
              <Slider
                min={20}
                max={400}
                step={10}
                value={markdownTypingSpeed}
                onChange={setMarkdownTypingSpeed}
                marks={{
                  60: "柔和",
                  120: "默认",
                  240: "快速",
                }}
              />
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  );
};

export { Settings };
