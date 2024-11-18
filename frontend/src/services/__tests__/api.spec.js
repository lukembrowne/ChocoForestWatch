import { describe, it, expect, vi } from 'vitest'
import api from '../api'

describe('API Service', () => {
    it('gets specific training polygons', async () => {
        // Mock the axios get request
        const mockResponse = {
            data: [{
                id: 1,
                name: "Test Training Set",
                basemap_date: "2023-01",
                polygons: { type: "FeatureCollection", features: [] }
            }]
        };
        
        vi.spyOn(api, 'getSpecificTrainingPolygons').mockResolvedValue(mockResponse);
        
        const response = await api.getSpecificTrainingPolygons(1, 1);
        
        expect(response.data).toHaveLength(1);
        expect(response.data[0].name).toBe("Test Training Set");
    });

    it('handles errors when getting training polygons', async () => {
        vi.spyOn(api, 'getSpecificTrainingPolygons').mockRejectedValue(new Error('Network error'));
        
        await expect(api.getSpecificTrainingPolygons(999, 999))
            .rejects
            .toThrow('Network error');
    });
}); 