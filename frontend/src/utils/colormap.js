// utils/colormap.js

  export const colormaps = {
    landcoverPalette: {
      0: [0, 128, 0],   // Forest – green
      1: [255, 255, 0],   // Non-forest – yellow
      2: [255, 255, 255], // Cloud – white
      3: [0,   0,   0],   // Shadow – black
      4: [0,   0, 255],   // Water – blue
      5: [255, 0, 0],   // Haze – red
      6: [128, 0, 128]   // Sensor Error – purple
    },
    CFWForestCoverPalette: {
      1: [0, 128, 0],   // Forest – green
      0: [255, 255, 0],   // Non-forest – yellow
      255: [0, 0, 0], // No data – black
    }
  };


  export function getEncodedColormap(name) {
    const palette = colormaps[name];
    if (!palette) {
      console.warn(`Colormap "${name}" not found.`);
      return '';
    }
    return encodeURIComponent(JSON.stringify(palette));
  }