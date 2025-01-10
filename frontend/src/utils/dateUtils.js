export function getBasemapDateOptions() {
    const options = []
    for (let year = 2022; year <= 2024; year++) {
      for (let month = 1; month <= 12; month++) {
        if (year === 2024 && month > 12) break // Put last month of imagery here
        const date = new Date(year, month - 1)
        options.push({
          label: date.toLocaleString('default', { month: 'long', year: 'numeric' }),
          value: `${year}-${month.toString().padStart(2, '0')}`
        })
      }
    }
    return options
  }