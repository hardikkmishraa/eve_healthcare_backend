import api from './api';
import type {
  DiagnosticCentre,
  DiagnosticTest,
  CentreTestOffering,
  PaginatedResponse,
} from '../types';

export const centreService = {
  async getCentres(params?: {
    city?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<DiagnosticCentre>> {
    const response = await api.get<PaginatedResponse<DiagnosticCentre>>('/centres', {
      params,
    });
    return response.data;
  },

  async getCentreById(id: string): Promise<DiagnosticCentre> {
    const response = await api.get<DiagnosticCentre>(`/centres/${id}`);
    return response.data;
  },

  async getCentreTests(centreId: string): Promise<CentreTestOffering[]> {
    const response = await api.get<CentreTestOffering[]>(`/centres/${centreId}/tests`);
    return response.data;
  },

  async getTests(params?: {
    category?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<DiagnosticTest>> {
    const response = await api.get<PaginatedResponse<DiagnosticTest>>('/tests', {
      params,
    });
    return response.data;
  },
};
