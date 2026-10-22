import { Badge, Brand, Timer } from "@/components/ui";
import { roundNames } from "@/lib/helpers";
import type { Common } from "@/types";
import { BookOpen, Maximize2, Radio } from "lucide-react";
export function Presentation({ state, notify }: Common) {
  const task = state.tasks.find((t) => t.id === state.current);
  return (
    <section className="presentation-screen">
      <div className="presentation-top">
        <Brand />
        <button
          className="button secondary"
          onClick={() =>
            void document.documentElement
              .requestFullscreen()
              .catch(() => notify("Fullscreen is unavailable."))
          }
        >
          <Maximize2 size={17} />
          Fullscreen
        </button>
      </div>
      {task ? (
        <>
          <div className="presentation-title">
            <div>
              <Badge tone="light">
                Round {task.round} / {roundNames[task.round - 1]}
              </Badge>
              <h1>{task.title}</h1>
            </div>
            <Timer task={task} state={state} large />
          </div>
          {task.round === 2 && task.reference_id ? (
            <img
              className="presentation-image"
              src={"/api/assets/" + task.reference_id}
              alt="Official reference displayed for all competing teams"
            />
          ) : task.round === 3 ? (
            <div className="presentation-brief">
              <p className="preserve">{task.brief}</p>
              {task.requirements && (
                <>
                  <h2>Brand requirements</h2>
                  <p className="preserve">{task.requirements}</p>
                </>
              )}
            </div>
          ) : (
            <div className="presentation-message">
              <BookOpen size={60} />
              <h2>Your knowledge takes the stage.</h2>
              <p>The quiz is available in each team’s private workspace.</p>
            </div>
          )}
        </>
      ) : (
        <div className="presentation-message">
          <Radio size={60} />
          <h1>Let the ideas begin.</h1>
          <p>
            The first round will appear here when the organizer releases it.
          </p>
        </div>
      )}
    </section>
  );
}
