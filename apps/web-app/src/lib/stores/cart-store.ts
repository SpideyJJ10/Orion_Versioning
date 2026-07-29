"use client";

import { create } from "zustand";
import type { Producto, MetodoPago, PagoMixto } from "@/lib/api/types";

export interface CartItem {
  producto:        Producto;
  cantidad:        number;       // decimal permitido
  precio_unitario: number;       // override del precio del producto si se desea
}

interface CartState {
  // ── Líneas ─────────────────────────────────────────
  items: CartItem[];

  // ── Datos del pago / cliente ───────────────────────
  cliente:           string;
  notas:             string;
  metodo_pago:       MetodoPago;
  descuento:         number;
  domicilio:         number;
  efectivo_recibido: number | null;
  pagos_mixtos:      PagoMixto[];

  // ── Acciones de líneas ─────────────────────────────
  add:        (producto: Producto, cantidad?: number) => void;
  remove:     (productoId: string) => void;
  setCantidad:(productoId: string, cantidad: number) => void;
  setPrecio:  (productoId: string, precio: number) => void;
  clear:      () => void;

  // ── Acciones del pago ──────────────────────────────
  setCliente:          (nombre: string) => void;
  setNotas:            (notas: string) => void;
  setMetodoPago:       (m: MetodoPago) => void;
  setDescuento:        (d: number) => void;
  setDomicilio:        (d: number) => void;
  setEfectivoRecibido: (e: number | null) => void;
  setPagosMixtos:      (p: PagoMixto[]) => void;

  // ── Selectores ─────────────────────────────────────
  subtotal:   () => number;
  total:      () => number;
  cambio:     () => number;
  totalItems: () => number;
}

const INITIAL = {
  items:             [] as CartItem[],
  cliente:           "",
  notas:             "",
  metodo_pago:       "Efectivo" as MetodoPago,
  descuento:         0,
  domicilio:         0,
  efectivo_recibido: null as number | null,
  pagos_mixtos:      [] as PagoMixto[],
};

export const useCartStore = create<CartState>((set, get) => ({
  ...INITIAL,

  add: (producto, cantidad = 1) => {
    const existing = get().items.find((i) => i.producto.id === producto.id);
    if (existing) {
      set({
        items: get().items.map((i) =>
          i.producto.id === producto.id
            ? { ...i, cantidad: round3(i.cantidad + cantidad) }
            : i,
        ),
      });
    } else {
      set({
        items: [
          ...get().items,
          { producto, cantidad: round3(cantidad), precio_unitario: producto.precio },
        ],
      });
    }
  },

  remove: (productoId) =>
    set({ items: get().items.filter((i) => i.producto.id !== productoId) }),

  setCantidad: (productoId, cantidad) => {
    if (cantidad <= 0) {
      get().remove(productoId);
      return;
    }
    set({
      items: get().items.map((i) =>
        i.producto.id === productoId ? { ...i, cantidad: round3(cantidad) } : i,
      ),
    });
  },

  setPrecio: (productoId, precio) =>
    set({
      items: get().items.map((i) =>
        i.producto.id === productoId
          ? { ...i, precio_unitario: Math.max(0, precio) }
          : i,
      ),
    }),

  clear: () => set({ ...INITIAL }),

  setCliente:          (cliente) => set({ cliente }),
  setNotas:            (notas) => set({ notas }),
  setMetodoPago:       (metodo_pago) => set({ metodo_pago }),
  setDescuento:        (descuento) => set({ descuento: Math.max(0, descuento) }),
  setDomicilio:        (domicilio) => set({ domicilio: Math.max(0, domicilio) }),
  setEfectivoRecibido: (efectivo_recibido) => set({ efectivo_recibido }),
  setPagosMixtos:      (pagos_mixtos) => set({ pagos_mixtos }),

  subtotal: () =>
    get().items.reduce((acc, i) => acc + i.precio_unitario * i.cantidad, 0),

  total: () => {
    const { descuento, domicilio } = get();
    return Math.max(0, get().subtotal() - descuento + domicilio);
  },

  cambio: () => {
    const { efectivo_recibido } = get();
    if (efectivo_recibido === null) return 0;
    return Math.max(0, efectivo_recibido - get().total());
  },

  totalItems: () => get().items.reduce((acc, i) => acc + i.cantidad, 0),
}));

function round3(n: number): number {
  return Math.round(n * 1000) / 1000;
}
