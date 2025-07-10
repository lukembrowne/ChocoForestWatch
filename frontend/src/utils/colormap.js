// utils/colormap.js

  export const colormaps = {
    landcoverPalette: {
      0: [34, 102, 51],   // Forest – dark green
      1: [205, 170, 125],   // Non-forest – light brown
      2: [255, 255, 255], // Cloud – white
      3: [0,   0,   0],   // Shadow – black
      4: [0,   0, 255],   // Water – blue
      5: [255, 0, 0],   // Haze – red
      6: [128, 0, 128]   // Sensor Error – purple
    },
    CFWForestCoverPalette: {
      1: [34, 102, 51],   // Forest – dark green
      0: [205, 170, 125],   // Non-forest – light brown
      255: [0, 0, 0], // No data – black
    },
    AlertPalette: {
      1: [255, 0, 0],   // Alert – red
      0: [0, 0, 0, 0],   // No alert - transparent
      255: [0, 0, 0], // No data – black
    },
    ColorBlindFriendlyAlertPalette: {
      1: [255, 140, 0],   // Alert – orange (color-blind friendly)
      0: [0, 0, 0, 0],    // No alert - transparent
      255: [0, 0, 0],     // No data – black
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