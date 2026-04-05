/**
 * Enhanced chat utilities for better message handling, loading states, and error recovery.
 */

export const ChatEnhancements = {
  // Message batching configuration
  messageBatching: {
    enabled: true,
    batchSize: 5,
    flushInterval: 500, // ms
  },

  // Streaming optimization
  streaming: {
    chunkSize: 50,
    maxRetries: 3,
    retryDelay: 500,
    timeout: 30000,
  },

  // Error recovery
  errorRecovery: {
    maxAttempts: 3,
    backoffMultiplier: 1.5,
    fallbackStrategies: [
      "reduce_context",
      "simplify_request",
      "show_last_partial",
    ],
  },
};

/**
 * Manage message batching for efficient rendering
 */
export class MessageBatcher {
  constructor(config = ChatEnhancements.messageBatching) {
    this.config = config;
    this.batch = [];
    this.flushTimer = null;
    this.onBatch = null;
  }

  add(message) {
    if (!this.config.enabled) {
      return;
    }

    this.batch.push(message);

    if (this.batch.length >= this.config.batchSize) {
      this.flush();
    } else if (!this.flushTimer) {
      this.flushTimer = setTimeout(() => this.flush(), this.config.flushInterval);
    }
  }

  flush() {
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }

    if (this.batch.length > 0 && this.onBatch) {
      this.onBatch([...this.batch]);
      this.batch = [];
    }
  }

  setOnBatch(callback) {
    this.onBatch = callback;
  }

  clear() {
    this.batch = [];
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
  }
}

/**
 * Smart retry mechanism for chat requests
 */
export class ChatRetryManager {
  constructor(config = ChatEnhancements.errorRecovery) {
    this.config = config;
    this.attempts = 0;
    this.lastError = null;
  }

  async executeWithRetry(fn, context = "") {
    this.attempts = 0;

    while (this.attempts < this.config.maxAttempts) {
      try {
        return await fn();
      } catch (error) {
        this.lastError = error;
        this.attempts++;

        if (this.attempts >= this.config.maxAttempts) {
          throw new Error(
            `Failed after ${this.config.maxAttempts} attempts: ${error.message}`
          );
        }

        const delay =
          ChatEnhancements.streaming.retryDelay *
          Math.pow(this.config.backoffMultiplier, this.attempts - 1);

        console.warn(
          `Retry ${this.attempts}/${this.config.maxAttempts} for ${context}. Waiting ${delay}ms...`
        );

        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  getSuggestedStrategy() {
    if (!this.lastError) return "reduce_context";

    const errorMessage = this.lastError.message.toLowerCase();

    if (
      errorMessage.includes("context") ||
      errorMessage.includes("token")
    ) {
      return "reduce_context";
    } else if (errorMessage.includes("timeout")) {
      return "simplify_request";
    } else {
      return "show_last_partial";
    }
  }

  reset() {
    this.attempts = 0;
    this.lastError = null;
  }
}

/**
 * Stream chunk optimizer - batches and debounces stream updates
 */
export class StreamOptimizer {
  constructor(config = ChatEnhancements.streaming) {
    this.config = config;
    this.buffer = "";
    this.lastFlush = Date.now();
    this.onChunk = null;
  }

  addChunk(chunk) {
    this.buffer += chunk;

    const timeSinceFlush = Date.now() - this.lastFlush;
    const shouldFlush =
      this.buffer.length >= this.config.chunkSize ||
      timeSinceFlush >= 100;

    if (shouldFlush) {
      this.flush();
    }
  }

  flush() {
    if (this.buffer && this.onChunk) {
      this.onChunk(this.buffer);
      this.buffer = "";
      this.lastFlush = Date.now();
    }
  }

  setOnChunk(callback) {
    this.onChunk = callback;
  }

  clear() {
    this.flush();
    this.buffer = "";
  }
}

/**
 * Context window manager - prevents context overflow
 */
export class ContextWindowManager {
  constructor(maxTokens = 4000) {
    this.maxTokens = maxTokens;
    this.reserveTokens = 500;
    this.messages = [];
  }

  estimateTokens(text) {
    // Rough estimate: 1 token ≈ 4 characters
    return Math.ceil(text.length / 4);
  }

  addMessage(message) {
    this.messages.push({
      ...message,
      estimatedTokens: this.estimateTokens(
        message.content + (message.role || "")
      ),
    });
  }

  getTotalTokens() {
    return this.messages.reduce((sum, msg) => sum + msg.estimatedTokens, 0);
  }

  canAddMessage(message) {
    const newTokens = this.estimateTokens(message.content);
    const total = this.getTotalTokens() + newTokens;
    const available = this.maxTokens - this.reserveTokens;

    return total <= available;
  }

  optimizeContext() {
    const total = this.getTotalTokens();
    const available = this.maxTokens - this.reserveTokens;

    if (total <= available) {
      return this.messages;
    }

    // Keep recent messages, drop older ones
    const optimized = [];
    let tokens = 0;

    // Keep last message (always important)
    if (this.messages.length > 0) {
      const last = this.messages[this.messages.length - 1];
      optimized.unshift(last);
      tokens += last.estimatedTokens;
    }

    // Keep recent messages until we hit limit
    for (let i = this.messages.length - 2; i >= 0; i--) {
      const msg = this.messages[i];
      if (tokens + msg.estimatedTokens <= available) {
        optimized.unshift(msg);
        tokens += msg.estimatedTokens;
      } else {
        break;
      }
    }

    return optimized;
  }
}

/**
 * Loading state manager for better UX
 */
export class LoadingStateManager {
  constructor() {
    this.states = new Map();
    this.callbacks = new Map();
  }

  setLoading(key, isLoading, metadata = {}) {
    const previous = this.states.get(key);
    this.states.set(key, { isLoading, ...metadata });

    if (this.callbacks.has(key)) {
      this.callbacks.get(key)({ isLoading, ...metadata });
    }

    return previous;
  }

  isLoading(key) {
    const state = this.states.get(key);
    return state ? state.isLoading : false;
  }

  onStateChange(key, callback) {
    this.callbacks.set(key, callback);
  }

  clear() {
    this.states.clear();
    this.callbacks.clear();
  }

  getStates() {
    return Object.fromEntries(this.states);
  }
}

/**
 * Enhanced error handler with recovery suggestions
 */
export class EnhancedErrorHandler {
  static handle(error, context = "") {
    const errorInfo = {
      message: error.message,
      type: error.constructor.name,
      timestamp: new Date().toISOString(),
      context,
    };

    // Categorize error
    let category = "unknown";
    let recovery = null;

    if (error.message.includes("context")) {
      category = "context_overflow";
      recovery = {
        suggestion: "Reduce conversation context",
        action: "reduce_context",
      };
    } else if (error.message.includes("timeout")) {
      category = "timeout";
      recovery = {
        suggestion: "Request timed out, retrying with simpler input...",
        action: "simplify_and_retry",
      };
    } else if (error.status === 429) {
      category = "rate_limit";
      recovery = {
        suggestion: "Rate limited, please wait before trying again",
        action: "wait_and_retry",
      };
    } else if (error.status >= 500) {
      category = "server_error";
      recovery = {
        suggestion: "Server error, trying again...",
        action: "retry",
      };
    } else if (error.status === 404) {
      category = "not_found";
      recovery = {
        suggestion: "Resource not found",
        action: "show_error",
      };
    }

    return {
      ...errorInfo,
      category,
      recovery,
    };
  }

  static format(error) {
    const handled = this.handle(error);
    return `${handled.category}: ${handled.message}`;
  }
}

/**
 * Hook-like utility for message effects (side effects without React)
 */
export class MessageEffectManager {
  constructor() {
    this.effects = [];
    this.cleanups = [];
  }

  registerEffect(fn, dependencies = []) {
    this.effects.push({ fn, dependencies });
  }

  async runEffects() {
    for (const effect of this.effects) {
      const cleanup = await effect.fn();
      if (typeof cleanup === "function") {
        this.cleanups.push(cleanup);
      }
    }
  }

  cleanup() {
    for (const cleanup of this.cleanups) {
      cleanup();
    }
    this.cleanups = [];
  }

  clear() {
    this.cleanup();
    this.effects = [];
  }
}
