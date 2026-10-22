import { Brand } from "@/components/ui";
import React from "react";
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="boot">
        <Brand />
        <h1>Let’s restore your workspace.</h1>
        <p>Your accepted work is stored on the server.</p>
        <button className="button primary" onClick={() => location.reload()}>
          Reload the application
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
