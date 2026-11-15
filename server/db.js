import mongoose from 'mongoose';

let connectionPromise;

export async function connectDatabase() {
  const uri = process.env.MONGODB_URI?.trim();
  if (!uri) return false;
  if (mongoose.connection.readyState === 1) return true;
  if (!connectionPromise) {
    connectionPromise = mongoose.connect(uri, {
      dbName: process.env.MONGODB_DB || 'dt_cargo',
      serverSelectionTimeoutMS: 5000,
      maxPoolSize: 5,
    }).then(() => true).catch((error) => {
      connectionPromise = undefined;
      throw error;
    });
  }
  return connectionPromise;
}

export function databaseReady() {
  return mongoose.connection.readyState === 1;
}
