import React from "react";

export default class GlobalErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    this.setState({ info });
    console.error("ISE AI UI boundary caught an error:", error, info);
  }

  reset = () => this.setState({ hasError: false, error: null, info: null });

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="global-error-boundary">
        <div className="global-error-card">
          <p className="eyebrow">UI recovery mode</p>
          <h2>Something in this panel failed to render.</h2>
          <p>The app stayed alive so you can retry, refresh, or continue working.</p>
          <pre>{String(this.state.error?.message || this.state.error || "Unknown UI error")}</pre>
          <button className="response-feedback-chip primary" onClick={this.reset}>Try rendering again</button>
        </div>
      </div>
    );
  }
}
