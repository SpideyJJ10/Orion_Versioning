import Dexie, { type Table } from 'dexie';

export interface LocalProduct {
  id: string;
  nombre: string;
  precio: number;
  stock: number;
  stock_minimo: number;
  categoria?: string;
  sucursal_id: string | null;
  activo: boolean;
}

export interface LocalCategory {
  id: string;
  nombre: string;
  activo: boolean;
  sucursal_id: string | null;
}

export interface LocalSucursal {
  id: string;
  nombre: string;
  activo: boolean;
}

export interface OfflineOrder {
  id: string;          // uuid local temporal
  payload: any;        // Datos de la orden que requiere la API
  timestamp: number;   // Fecha creación
  status: 'pending' | 'syncing' | 'failed';
  error?: string;
}

export class OrionDatabase extends Dexie {
  products!: Table<LocalProduct, string>;
  categories!: Table<LocalCategory, string>;
  sucursales!: Table<LocalSucursal, string>;
  offlineOrders!: Table<OfflineOrder, string>;

  constructor() {
    super('Orion_OfflineDB');
    this.version(2).stores({
      products: 'id, nombre, categoria, sucursal_id',
      categories: 'id, nombre, sucursal_id',
      sucursales: 'id, nombre',
      offlineOrders: 'id, status, timestamp'
    });
  }
}

export const db = new OrionDatabase();
