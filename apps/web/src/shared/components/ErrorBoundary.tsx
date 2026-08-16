import { Component, type ErrorInfo, type ReactNode } from "react";

type ErrorBoundaryProps = { children: ReactNode };
type ErrorBoundaryState = { hasError: boolean };

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("FoxPilot UI error", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="error-boundary">
        <p className="eyebrow accent">FOXPILOT</p>
        <h1>Something interrupted this view.</h1>
        <p>Reload the page to return to your private workspace.</p>
        <button className="primary-button" type="button" onClick={() => window.location.reload()}>
          Reload FoxPilot
        </button>
      </main>
    );
  }
}
