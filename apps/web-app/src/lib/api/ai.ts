import { api } from "./client";

export interface AIConfigResponse {
  message: string;
  config: {
    branding: {
      nombre_comercial: string;
      nicho: string;
      tema: string;
      color_primary: string;
      color_secondary: string;
      color_accent: string;
    };
    categorias: string[];
    productos_sugeridos: Array<{
      nombre: string;
      precio: number;
      categoria: string;
    }>;
    metodos_pago: string[];
  };
}

export const aiApi = {
  generatePOS: (description: string) => {
    return api.post<AIConfigResponse>("/api/v3/ai/generate-pos", { description });
  },
};
