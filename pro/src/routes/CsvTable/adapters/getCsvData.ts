import { ITableData } from 'screens/CsvTable'
import csvConverter from 'utils/csvConverter'

export const getCsvData = (csvUrl: string): Promise<ITableData | null> => {
  return new Promise((resolve, reject) => {
    ;(async () => {
      try {
        const result = await fetch(csvUrl, { credentials: 'include' })
        const { status } = result
        if (status === 200) {
          const text = await result.text()
          resolve(csvConverter(text))
        } else {
          reject(null)
        }
      } catch (error) {
        reject(null)
      }
    })()
  })
}
