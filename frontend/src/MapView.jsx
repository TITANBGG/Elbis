import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'

export default function MapView({ events = [] }) {
  const center = [39.9, 32.8]
  return (
    <MapContainer center={center} zoom={6} style={{ height: '100%', width: '100%' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {events.map((e) => (
        <Marker key={e.id} position={[e.lat, e.lon]}>
          <Popup>{e.title}</Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
