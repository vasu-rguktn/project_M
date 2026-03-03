import { Line } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from 'chart.js'
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

export default function PortfolioChart({ points = [100,110,120,115,130] }){
  const labels = points.map((_,i) => `T-${points.length - i}`)
  const data = {
    labels,
    datasets: [
      {
        label: 'Portfolio Value',
        data: points,
        fill: false,
        tension: 0.2
      }
    ]
  }
  return <Line data={data} />
}

