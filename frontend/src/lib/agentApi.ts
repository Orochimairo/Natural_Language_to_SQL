import type {
  AgentEvent,
  ProgressStatus,
  QueryResultRow,
} from "../types/agent";

type QueryOptions = {
  signal?: AbortSignal;
  onEvent: (event: AgentEvent) => void;
};

export async function streamQuery(
  query: string,
  options: QueryOptions,
): Promise<string | null> {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      query,
    }),
    signal: options.signal,
  });

  if (!response.ok) {
    const responseText = await response.text();

    throw new Error(
      `接口请求失败：HTTP ${response.status} ${
        responseText || response.statusText
      }`,
    );
  }

  const contentType =
    response.headers.get("content-type") ?? "";

  if (!contentType.startsWith("text/event-stream")) {
    throw new Error(
      `接口响应类型不是 SSE：${contentType}`,
    );
  }

  if (!response.body) {
    throw new Error(
      "浏览器未返回可读取的流式响应",
    );
  }

  const requestId =
    response.headers.get("X-Request-ID");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, {
      stream: true,
    });

    const frames = buffer.split(
      /\r?\n\r?\n/,
    );

    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const event = parseSseFrame(frame);

      if (event) {
        options.onEvent(event);
      }
    }
  }

  buffer += decoder.decode();

  const finalEvent = parseSseFrame(buffer);

  if (finalEvent) {
    options.onEvent(finalEvent);
  }

  return requestId;
}

function parseSseFrame(
  frame: string,
): AgentEvent | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) =>
      line.replace(/^data:\s?/, ""),
    )
    .join("\n")
    .trim();

  if (!data) {
    return null;
  }

  let value: unknown;

  try {
    value = JSON.parse(data);
  } catch {
    throw new Error(
      `无法解析后端 SSE JSON：${data}`,
    );
  }

  return parseAgentEvent(value);
}

function parseAgentEvent(
  value: unknown,
): AgentEvent {
  if (!isRecord(value)) {
    throw new Error(
      "后端 SSE 事件必须是 JSON 对象",
    );
  }

  if (value.type === "progress") {
    if (
      typeof value.step !== "string" ||
      !isProgressStatus(value.status)
    ) {
      throw new Error(
        "后端 progress 事件结构不正确",
      );
    }

    return {
      type: "progress",
      step: value.step,
      status: value.status,
    };
  }

  if (value.type === "result") {
    if (
      !Array.isArray(value.data) ||
      !value.data.every(isQueryResultRow)
    ) {
      throw new Error(
        "后端 result 事件 data 必须是对象数组",
      );
    }

    return {
      type: "result",
      data: value.data,
    };
  }

  if (value.type === "error") {
    if (typeof value.message !== "string") {
      throw new Error(
        "后端 error 事件缺少 message",
      );
    }

    return {
      type: "error",
      message: value.message,
    };
  }

  throw new Error(
    `后端返回了未知事件类型：${String(
      value.type,
    )}`,
  );
}

function isProgressStatus(
  value: unknown,
): value is ProgressStatus {
  return (
    value === "running" ||
    value === "success" ||
    value === "error"
  );
}

function isQueryResultRow(
  value: unknown,
): value is QueryResultRow {
  return isRecord(value);
}

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}
