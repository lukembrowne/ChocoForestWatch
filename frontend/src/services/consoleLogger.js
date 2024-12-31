class ConsoleLogger {
  constructor() {
    this.logs = []
    this.setupConsoleInterceptor()
  }

  setupConsoleInterceptor() {
    const methods = ['log', 'info', 'warn', 'error']
    methods.forEach(method => {
      const originalMethod = console[method]
      console[method] = (...args) => {
        // Call original console method
        originalMethod.apply(console, args)
        
        // Store the log
        this.logs.push({
          type: method,
          message: args.map(arg => {
            try {
              return typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
            } catch (e) {
              return String(arg)
            }
          }).join(' '),
          timestamp: Date.now()
        })

        // Keep only last 1000 logs
        if (this.logs.length > 1000) {
          this.logs.shift()
        }
      }
    })
  }

  getRecentLogs(duration = 3600000) { // default 1 hour
    const cutoff = Date.now() - duration
    return this.logs.filter(log => log.timestamp > cutoff)
  }

  clearLogs() {
    this.logs = []
  }
}

export const consoleLogger = new ConsoleLogger() 