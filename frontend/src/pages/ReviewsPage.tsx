import { useEffect, useState } from "react";

import {
  assignReviewCase,
  decideReviewCase,
  fetchReviewHistory,
  fetchReviewQueue,
  fetchReviewSuggestion,
} from "../services/api";
import type { ReviewEvent, ReviewQueueItem, ReviewSuggestion, RiskDecision } from "../types";

interface ReviewsPageProps {
  token: string;
}

export function ReviewsPage({ token }: ReviewsPageProps) {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ReviewQueueItem | null>(null);
  const [history, setHistory] = useState<ReviewEvent[]>([]);
  const [suggestion, setSuggestion] = useState<ReviewSuggestion | null>(null);

  const [assignedTo, setAssignedTo] = useState("reviewer@meridian.ai");
  const [assignNote, setAssignNote] = useState("Assigned from review queue.");
  const [decision, setDecision] = useState<RiskDecision>("review");
  const [decisionNote, setDecisionNote] = useState("Manual review completed.");

  async function loadQueue() {
    try {
      setLoading(true);
      setError(null);
      const payload = await fetchReviewQueue(token);
      setItems(payload.items);
      if (!selected && payload.items.length) {
        setSelected(payload.items[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load review queue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQueue();
  }, [token]);

  useEffect(() => {
    async function loadCaseDetails() {
      if (!selected) {
        setHistory([]);
        setSuggestion(null);
        return;
      }

      try {
        const [historyPayload, suggestionPayload] = await Promise.all([
          fetchReviewHistory(token, selected.transaction_id),
          fetchReviewSuggestion(token, selected.transaction_id),
        ]);
        setHistory(historyPayload);
        setSuggestion(suggestionPayload);
      } catch {
        setHistory([]);
        setSuggestion(null);
      }
    }

    loadCaseDetails();
  }, [selected, token]);

  async function onAssign() {
    if (!selected) return;
    await assignReviewCase(token, selected.transaction_id, assignedTo, assignNote);
    await loadQueue();
  }

  async function onDecision() {
    if (!selected) return;
    await decideReviewCase(token, selected.transaction_id, decision, decisionNote);
    await loadQueue();
  }

  if (loading) return <p className="state">Loading review queue...</p>;
  if (error) return <p className="state error">{error}</p>;

  return (
    <div className="review-grid">
      <section className="panel">
        <h2>Manual Review Queue</h2>
        {!items.length ? <p className="state">No pending review cases.</p> : null}
        <ul className="review-list">
          {items.map((item) => (
            <li
              key={item.case_id}
              className={selected?.case_id === item.case_id ? "review-item active" : "review-item"}
              onClick={() => setSelected(item)}
            >
              <div>
                <strong>TX #{item.transaction_id}</strong>
                <p>{item.explanation_summary}</p>
              </div>
              <span className={`text-${item.final_decision}`}>{item.final_decision.toUpperCase()}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Analyst Workbench</h2>
        {selected ? (
          <>
            <p>
              <strong>Case #{selected.case_id}</strong> · TX #{selected.transaction_id}
            </p>
            <div className="flags">
              {selected.reason_codes.map((code) => (
                <span key={code}>{code}</span>
              ))}
            </div>

            {suggestion ? (
              <div className="state">
                <strong>AI Suggestion:</strong> {suggestion.suggested_decision.toUpperCase()} ({Math.round(suggestion.confidence * 100)}%)
                <p>{suggestion.rationale}</p>
              </div>
            ) : null}

            <div className="review-actions">
              <h3>Assign</h3>
              <input value={assignedTo} onChange={(event) => setAssignedTo(event.target.value)} placeholder="Assignee email" />
              <input value={assignNote} onChange={(event) => setAssignNote(event.target.value)} placeholder="Assignment note" />
              <button className="inline-btn" onClick={onAssign}>Assign Case</button>
            </div>

            <div className="review-actions">
              <h3>Decision</h3>
              <select value={decision} onChange={(event) => setDecision(event.target.value as RiskDecision)}>
                <option value="approve">Approve</option>
                <option value="review">Review</option>
                <option value="decline">Decline</option>
              </select>
              <input value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} placeholder="Decision note" />
              <button className="inline-btn" onClick={onDecision}>Submit Decision</button>
            </div>

            <h3>Case History</h3>
            <ul className="history-list">
              {history.map((event) => (
                <li key={event.id}>
                  <strong>{event.action}</strong> · {event.actor_email}
                  <p>{event.note}</p>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="state">Select a case to review details.</p>
        )}
      </section>
    </div>
  );
}
