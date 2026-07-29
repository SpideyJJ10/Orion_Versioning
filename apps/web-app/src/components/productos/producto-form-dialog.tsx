"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCategorias,
  useCrearProducto,
  useActualizarProducto,
} from "@/lib/hooks/use-api";
import type {
  Producto,
  ProductoCrearRequest,
  ProductoActualizarRequest,
  UnidadMedida,
} from "@/lib/api/types";

const UNIDADES: { value: UnidadMedida; label: string; decimal: boolean }[] = [
  { value: "unidad", label: "Unidad",  decimal: false },
  { value: "kg",     label: "Kilo",    decimal: true  },
  { value: "lt",     label: "Litro",   decimal: true  },
  { value: "gr",     label: "Gramo",   decimal: true  },
  { value: "ml",     label: "Mililitro", decimal: true },
  { value: "pack",   label: "Pack",    decimal: false },
  { value: "caja",   label: "Caja",    decimal: false },
  { value: "docena", label: "Docena",  decimal: false },
];

interface ProductoFormDialogProps {
  open:         boolean;
  onOpenChange: (open: boolean) => void;
  /** Si se pasa, modo edición; si no, modo creación. */
  producto?:    Producto | null;
  /** Sucursal por defecto al crear. */
  sucursalId:   string;
}

interface FormState {
  nombre:        string;
  precio:        string;
  costo:         string;
  categoria:     string;
  sku:           string;
  descripcion:   string;
  unidad_medida: UnidadMedida;
  stock:         string;
  stock_minimo:  string;
  imagen_url:    string;
  insumos:       string;
}

const EMPTY: FormState = {
  nombre:        "",
  precio:        "",
  costo:         "",
  categoria:     "",
  sku:           "",
  descripcion:   "",
  unidad_medida: "unidad",
  stock:         "",
  stock_minimo:  "",
  imagen_url:    "",
  insumos:       "",
};

/**
 * Diálogo para crear o editar un producto.
 *
 * - Soporta creación de categoría al vuelo (escribe el nombre y al guardar
 *   el backend crea la categoría si no existe — endpoint POST /api/productos
 *   ya hace esto cuando el cuerpo trae `categoria` por nombre).
 * - El campo `stock` solo se respeta en creación (en edición se usa el
 *   diálogo de ajuste, que escribe ledger).
 */
export function ProductoFormDialog({
  open,
  onOpenChange,
  producto,
  sucursalId,
}: ProductoFormDialogProps) {
  const isEdit = !!producto;

  const [form, setForm] = useState<FormState>(EMPTY);

  const categoriasQ = useCategorias(sucursalId);
  const crearM = useCrearProducto();
  const updM   = useActualizarProducto();

  useEffect(() => {
    if (!open) return;
    if (producto) {
      setForm({
        nombre:        producto.nombre,
        precio:        String(producto.precio),
        costo:         String(producto.costo ?? 0),
        categoria:     producto.categoria || "",
        sku:           producto.sku ?? "",
        descripcion:   producto.descripcion ?? "",
        unidad_medida: (producto.unidad_medida as UnidadMedida) || "unidad",
        stock:         String(producto.stock),
        stock_minimo:  String(producto.stock_minimo),
        imagen_url:    producto.imagen_url ?? "",
        insumos:       producto.insumos ?? "",
      });
    } else {
      setForm(EMPTY);
    }
  }, [open, producto]);

  const isPending = crearM.isPending || updM.isPending;

  function handleChange<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.nombre.trim() || !form.precio) return;

    const base: ProductoCrearRequest = {
      sucursal_id:   sucursalId,
      nombre:        form.nombre.trim(),
      precio:        Number(form.precio),
      costo:         form.costo === "" ? 0 : Number(form.costo),
      categoria:     form.categoria.trim() || undefined,
      sku:           form.sku.trim() || null,
      descripcion:   form.descripcion.trim() || null,
      imagen_url:    form.imagen_url.trim() || null,
      unidad_medida: form.unidad_medida,
      stock:         form.stock === "" ? 0 : Number(form.stock),
      stock_minimo:  form.stock_minimo === "" ? 0 : Number(form.stock_minimo),
      insumos:       form.insumos.trim() || undefined,
    };

    try {
      if (isEdit && producto) {
        const update: ProductoActualizarRequest = { ...base };
        // En edición no enviamos `stock` (se ajusta vía ledger).
        delete update.stock;
        await updM.mutateAsync({ id: producto.id, data: update });
      } else {
        await crearM.mutateAsync(base);
      }
      onOpenChange(false);
    } catch {
      /* toast desde el hook */
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar producto" : "Nuevo producto"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Cambia datos del producto. El stock se ajusta desde Inventario."
              : "Completa los datos para añadir el producto al catálogo."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nombre" required>
              <Input
                value={form.nombre}
                onChange={(e) => handleChange("nombre", e.target.value)}
                required
                autoFocus
              />
            </Field>
            <Field label="SKU (opcional)">
              <Input
                value={form.sku}
                onChange={(e) => handleChange("sku", e.target.value)}
              />
            </Field>

            <Field label="Precio venta" required>
              <Input
                type="number"
                step="0.01"
                inputMode="decimal"
                min={0}
                value={form.precio}
                onChange={(e) => handleChange("precio", e.target.value)}
                required
              />
            </Field>
            <Field label="Costo">
              <Input
                type="number"
                step="0.01"
                inputMode="decimal"
                min={0}
                value={form.costo}
                onChange={(e) => handleChange("costo", e.target.value)}
              />
            </Field>

            <Field label="Categoría">
              <CategoriaInput
                value={form.categoria}
                options={(categoriasQ.data ?? []).map((c) => c.nombre)}
                onChange={(v) => handleChange("categoria", v)}
              />
            </Field>
            <Field label="Unidad de medida">
              <Select
                value={form.unidad_medida}
                onValueChange={(v) => handleChange("unidad_medida", v as UnidadMedida)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {UNIDADES.map((u) => (
                    <SelectItem key={u.value} value={u.value}>
                      {u.label} {u.decimal ? "(decimal)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            {!isEdit && (
              <Field label="Stock inicial">
                <Input
                  type="number"
                  step="0.001"
                  inputMode="decimal"
                  min={0}
                  value={form.stock}
                  onChange={(e) => handleChange("stock", e.target.value)}
                />
              </Field>
            )}
            <Field label="Stock mínimo">
              <Input
                type="number"
                step="0.001"
                inputMode="decimal"
                min={0}
                value={form.stock_minimo}
                onChange={(e) => handleChange("stock_minimo", e.target.value)}
              />
            </Field>

            <Field label="URL de imagen" colSpan={2}>
              <Input
                type="url"
                placeholder="https://…"
                value={form.imagen_url}
                onChange={(e) => handleChange("imagen_url", e.target.value)}
              />
            </Field>

            <Field label="Descripción" colSpan={2}>
              <Textarea
                rows={2}
                value={form.descripcion}
                onChange={(e) => handleChange("descripcion", e.target.value)}
              />
            </Field>
          </div>

          <DialogFooter className="gap-2 sm:justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEdit ? "Guardar" : "Crear producto"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  required,
  children,
  colSpan,
}: {
  label:    string;
  required?: boolean;
  children: React.ReactNode;
  colSpan?: 1 | 2;
}) {
  return (
    <div className={`space-y-1 ${colSpan === 2 ? "col-span-2" : ""}`}>
      <Label className="text-xs">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
    </div>
  );
}

/**
 * Input de categoría con autocompletado básico (datalist nativo).
 * Permite escribir una nueva categoría que el backend creará al guardar.
 */
function CategoriaInput({
  value,
  options,
  onChange,
}: {
  value:    string;
  options:  string[];
  onChange: (v: string) => void;
}) {
  return (
    <>
      <Input
        list="orion-categorias"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Bebidas, Comida, Servicios…"
      />
      <datalist id="orion-categorias">
        {options.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </>
  );
}
