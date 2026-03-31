import React from "react";
import "./utils/console_logger.js";  // Auto-generated console logger
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/global.css";

// Mount the React application once and let App own all runtime state.
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
