import { db } from './db';
import { api } from './api/client';

export class SyncManager {
  private isOnline: boolean = navigator.onLine;
  private syncInProgress: boolean = false;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline.bind(this));
      window.addEventListener('offline', this.handleOffline.bind(this));
    }
  }

  private handleOnline() {
    this.isOnline = true;
    console.log('[SyncManager] Online mode restored. Syncing offline queue...');
    this.syncOfflineOrders();
  }

  private handleOffline() {
    this.isOnline = false;
    console.log('[SyncManager] Offline mode active. Operations will be queued locally.');
  }

  public getOnlineStatus() {
    return this.isOnline;
  }

  public async queueOrder(orderPayload: any) {
    const id = crypto.randomUUID();
    await db.offlineOrders.add({
      id,
      payload: orderPayload,
      timestamp: Date.now(),
      status: 'pending'
    });
    
    // Attempt sync immediately if online
    if (this.isOnline) {
      this.syncOfflineOrders();
    }
    return id;
  }

  public async syncOfflineOrders() {
    if (!this.isOnline || this.syncInProgress) return;
    
    this.syncInProgress = true;
    
    try {
      const pendingOrders = await db.offlineOrders.where('status').equals('pending').toArray();
      if (pendingOrders.length === 0) {
        this.syncInProgress = false;
        return;
      }

      for (const order of pendingOrders) {
        try {
          // Mark as syncing
          await db.offlineOrders.update(order.id, { status: 'syncing' });
          
          // Send to backend via our standard api client
          await api.post('/api/v3/ordenes/', order.payload);
          
          // Success: Remove from queue
          await db.offlineOrders.delete(order.id);
        } catch (error: any) {
          console.error(`[SyncManager] Failed to sync order ${order.id}:`, error);
          // Mark back as pending to retry later
          await db.offlineOrders.update(order.id, { 
            status: 'pending',
            error: error?.message || 'Unknown error'
          });
        }
      }
    } finally {
      this.syncInProgress = false;
    }
  }
}

export const syncManager = new SyncManager();
