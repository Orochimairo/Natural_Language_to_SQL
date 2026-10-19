import {
  type FormEvent,
  useRef,
  useState,
} from "react";

import "./App.css";
import { streamQuery } from "./lib/agentApi";
import type {
  AgentEvent,
  ProgressEvent,
  QueryResultRow,
} from "./types/agent";

const DEFAULT_QUERY =
  "华东地区 iPhone 的销售总额是多少？";

function App() {
  const [query, setQuery] = useState(
    DEFAULT_QUERY,
  );
  const [steps, setSteps] = useState<
    ProgressEvent[]
  >([]);
  const [result, setResult] = useState<
    QueryResultRow[] | null
  >(null);
  const [error, setError] = useState<
    string | null
  >(null);
  const [requestId, setRequestId] = useState<
    string | null
  >(null);
  const [isRunning, setIsRunning] =
    useState(false);

  const abortControllerRef =
    useRef<AbortController | null>(null);

  function handleEvent(event: AgentEvent) {
    if (event.type === "progress") {
      setSteps((currentSteps) => {
        const existingStep =
          currentSteps.some(
            (step) => step.step === event.step,
          );

        if (!existingStep) {
          return [...currentSteps, event];
        }

        return currentSteps.map((step) =>
          step.step === event.step
            ? event
            : step,
        );
      });

      return;
    }

    if (event.type === "result") {
      setResult(event.data);
      return;
    }

    setError(event.message);
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedQuery = query.trim();

    if (!normalizedQuery) {
      setError("请输入需要查询的问题");
      return;
    }

    setSteps([]);
    setResult(null);
    setError(null);
    setRequestId(null);
    setIsRunning(true);

    const abortController =
      new AbortController();

    abortControllerRef.current =
      abortController;

    try {
      const responseRequestId =
        await streamQuery(normalizedQuery, {
          signal: abortController.signal,
          onEvent: handleEvent,
        });

      setRequestId(responseRequestId);
    } catch (requestError) {
      if (
        requestError instanceof Error &&
        requestError.name === "AbortError"
      ) {
        setError("查询已取消");
      } else if (
        requestError instanceof Error
      ) {
        setError(requestError.message);
      } else {
        setError("查询发生未知错误");
      }
    } finally {
      abortControllerRef.current = null;
      setIsRunning(false);
    }
  }

  function handleCancel() {
    abortControllerRef.current?.abort();
  }

  const columns =
    result && result.length > 0
      ? Object.keys(result[0])
      : [];

  return (
    <main className="app-shell">
      <section className="query-panel">
        <header>
          <p className="eyebrow">
            Natural Language to SQL
          </p>
          <h1>自然语言转SQL</h1>
          <p className="description">
            输入业务问题，查看 LangGraph
            执行进度和数据库查询结果。
          </p>
        </header>

        <form
          className="query-form"
          onSubmit={handleSubmit}
        >
          <label htmlFor="query">
            查询问题
          </label>

          <textarea
            id="query"
            value={query}
            onChange={(event) =>
              setQuery(event.target.value)
            }
            disabled={isRunning}
            rows={4}
          />

          <div className="actions">
            <button
              type="submit"
              disabled={isRunning}
            >
              {isRunning
                ? "查询中..."
                : "开始查询"}
            </button>

            {isRunning && (
              <button
                type="button"
                className="secondary"
                onClick={handleCancel}
              >
                取消查询
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="output-panel">
        <div className="output-card">
          <h2>执行进度</h2>

          {steps.length === 0 ? (
            <p className="empty">
              提交问题后将在这里显示节点状态。
            </p>
          ) : (
            <ol className="step-list">
              {steps.map((step) => (
                <li key={step.step}>
                  <span>{step.step}</span>
                  <strong
                    className={`status ${step.status}`}
                  >
                    {step.status}
                  </strong>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div className="output-card">
          <h2>查询结果</h2>

          {error && (
            <p className="error-message">
              {error}
            </p>
          )}

          {!error && !result && (
            <p className="empty">
              暂无查询结果。
            </p>
          )}

          {result && result.length === 0 && (
            <p className="empty">
              查询成功，但没有返回数据。
            </p>
          )}

          {result && result.length > 0 && (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    {columns.map((column) => (
                      <th key={column}>
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {columns.map((column) => (
                        <td key={column}>
                          {String(
                            row[column] ?? "",
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {requestId && (
            <p className="request-id">
              Request ID：{requestId}
            </p>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
