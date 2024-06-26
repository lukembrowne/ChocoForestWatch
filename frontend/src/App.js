import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, ImageOverlay } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function App() {
  const [imageUrl, setImageUrl] = useState('');

  useEffect(() => {
    fetch('/load-raster')
      .then(response => response.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        setImageUrl(url);
      });
  }, []);

  return (
    <div className="App">
      <MapContainer center={[0, 0]} zoom={2} style={{ height: '100vh', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        {imageUrl && (
          <ImageOverlay
            url={imageUrl}
          />
        )}
      </MapContainer>
    </div>
  );
}

export default App;