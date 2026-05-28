import React, { useEffect, useState } from 'react'
import MapView from './MapView'

export default function App() {
  const [events, setEvents] = useState([])

  useEffect(() => {
    fetch('http://localhost:8000/events')
      .then((r) => r.json())
      .then(setEvents)
      .catch((e) => console.error(e))
  }, [])

  return (
    <div style={{ height: '100vh' }}>
      <MapView events={events} />
    </div>
  )
}
