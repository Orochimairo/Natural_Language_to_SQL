export type ProgressStatus =
  | "running"
  | "success"
  | "error";

export type ProgressEvent = {
  type: "progress";
  step: string;
  status: ProgressStatus;
};

export type QueryResultRow = Record<
  string,
  unknown
>;

export type ResultEvent = {
  type: "result";
  data: QueryResultRow[];
};

export type ErrorEvent = {
  type: "error";
  message: string;
};

export type AgentEvent =
  | ProgressEvent
  | ResultEvent
  | ErrorEvent;
