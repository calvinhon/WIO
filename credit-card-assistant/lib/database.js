// lib/database.js
const { MongoClient } = require('mongodb');
const fs = require('fs').promises;
const path = require('path');

class Database {
    constructor(connectionString = null) {
        this.connectionString = connectionString || process.env.MONGODB_URI;
        this.client = null;
        this.db = null;
        this.useFileStorage = !this.connectionString;
        this.dataDir = path.join(__dirname, '../data');
        this.billsFile = path.join(this.dataDir, 'bills.json');
        this.transactionsFile = path.join(this.dataDir, 'transactions.json');
        
        if (this.useFileStorage) {
            this.initFileStorage();
        }
    }
    
    async initFileStorage() {
        try {
            await fs.mkdir(this.dataDir, { recursive: true });
            
            // Initialize files if they don't exist
            try {
                await fs.access(this.billsFile);
            } catch {
                await fs.writeFile(this.billsFile, '[]');
            }
            
            try {
                await fs.access(this.transactionsFile);
            } catch {
                await fs.writeFile(this.transactionsFile, '[]');
            }
            
            console.log('File storage initialized');
        } catch (error) {
            console.error('Error initializing file storage:', error);
        }
    }
    
    async connect() {
        if (this.useFileStorage) {
            console.log('Using file storage (no MongoDB connection)');
            return;
        }
        
        try {
            this.client = new MongoClient(this.connectionString);
            await this.client.connect();
            this.db = this.client.db('creditcard_assistant');
            console.log('Connected to MongoDB');
        } catch (error) {
            console.error('MongoDB connection failed, falling back to file storage:', error);
            this.useFileStorage = true;
            await this.initFileStorage();
        }
    }
    
    async disconnect() {
        if (this.client) {
            await this.client.close();
            console.log('Disconnected from MongoDB');
        }
    }
    
    async storeBill(bill) {
        if (this.useFileStorage) {
            return await this.storeBillFile(bill);
        }
        
        try {
            const collection = this.db.collection('bills');
            bill.createdAt = new Date().toISOString();
            bill.updatedAt = new Date().toISOString();
            
            const result = await collection.insertOne(bill);
            console.log(`Bill stored with ID: ${result.insertedId}`);
            return result.insertedId;
        } catch (error) {
            console.error('Error storing bill:', error);
            throw error;
        }
    }
    
    async storeBillFile(bill) {
        try {
            const bills = await this.readJsonFile(this.billsFile);
            bill.createdAt = new Date().toISOString();
            bill.updatedAt = new Date().toISOString();
            bills.push(bill);
            await this.writeJsonFile(this.billsFile, bills);
            console.log(`Bill stored to file: ${bill.id}`);
            return bill.id;
        } catch (error) {
            console.error('Error storing bill to file:', error);
            throw error;
        }
    }
    
    async getBills(userId = 'default', filter = {}) {
        if (this.useFileStorage) {
            return await this.getBillsFile(userId, filter);
        }
        
        try {
            const collection = this.db.collection('bills');
            const query = { userId, ...filter };
            const bills = await collection.find(query).sort({ createdAt: -1 }).toArray();
            return bills;
        } catch (error) {
            console.error('Error retrieving bills:', error);
            throw error;
        }
    }
    
    async getBillsFile(userId = 'default', filter = {}) {
        try {
            const bills = await this.readJsonFile(this.billsFile);
            let filteredBills = bills.filter(bill => bill.userId === userId);
            
            // Apply additional filters
            if (filter.status) {
                filteredBills = filteredBills.filter(bill => bill.status === filter.status);
            }
            if (filter.bank) {
                filteredBills = filteredBills.filter(bill => bill.bank === filter.bank);
            }
            
            // Sort by creation date (newest first)
            filteredBills.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
            
            return filteredBills;
        } catch (error) {
            console.error('Error retrieving bills from file:', error);
            throw error;
        }
    }
    
    async updateBillStatus(billId, status) {
        if (this.useFileStorage) {
            return await this.updateBillStatusFile(billId, status);
        }
        
        try {
            const collection = this.db.collection('bills');
            const result = await collection.updateOne(
                { id: billId },
                { 
                    $set: { 
                        status: status,
                        updatedAt: new Date().toISOString()
                    }
                }
            );
            return result.modifiedCount > 0;
        } catch (error) {
            console.error('Error updating bill status:', error);
            throw error;
        }
    }
    
    async updateBillStatusFile(billId, status) {
        try {
            const bills = await this.readJsonFile(this.billsFile);
            const billIndex = bills.findIndex(bill => bill.id === billId);
            
            if (billIndex !== -1) {
                bills[billIndex].status = status;
                bills[billIndex].updatedAt = new Date().toISOString();
                await this.writeJsonFile(this.billsFile, bills);
                return true;
            }
            return false;
        } catch (error) {
            console.error('Error updating bill status in file:', error);
            throw error;
        }
    }
    
    async storeTransaction(transaction) {
        if (this.useFileStorage) {
            return await this.storeTransactionFile(transaction);
        }
        
        try {
            const collection = this.db.collection('transactions');
            transaction.createdAt = new Date().toISOString();
            
            const result = await collection.insertOne(transaction);
            console.log(`Transaction stored with ID: ${result.insertedId}`);
            return result.insertedId;
        } catch (error) {
            console.error('Error storing transaction:', error);
            throw error;
        }
    }
    
    async storeTransactionFile(transaction) {
        try {
            const transactions = await this.readJsonFile(this.transactionsFile);
            transaction.createdAt = new Date().toISOString();
            transactions.push(transaction);
            await this.writeJsonFile(this.transactionsFile, transactions);
            console.log(`Transaction stored to file: ${transaction.id}`);
            return transaction.id;
        } catch (error) {
            console.error('Error storing transaction to file:', error);
            throw error;
        }
    }
    
    async getTransactions(userId = 'default', filter = {}) {
        if (this.useFileStorage) {
            return await this.getTransactionsFile(userId, filter);
        }
        
        try {
            const collection = this.db.collection('transactions');
            const query = { userId, ...filter };
            const transactions = await collection.find(query).sort({ createdAt: -1 }).toArray();
            return transactions;
        } catch (error) {
            console.error('Error retrieving transactions:', error);
            throw error;
        }
    }
    
    async getTransactionsFile(userId = 'default', filter = {}) {
        try {
            const transactions = await this.readJsonFile(this.transactionsFile);
            let filteredTransactions = transactions.filter(t => t.userId === userId);
            
            // Apply additional filters
            if (filter.type) {
                filteredTransactions = filteredTransactions.filter(t => t.type === filter.type);
            }
            
            // Sort by creation date (newest first)
            filteredTransactions.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
            
            return filteredTransactions;
        } catch (error) {
            console.error('Error retrieving transactions from file:', error);
            throw error;
        }
    }
    
    async readJsonFile(filePath) {
        try {
            const data = await fs.readFile(filePath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error(`Error reading ${filePath}:`, error);
            return [];
        }
    }
    
    async writeJsonFile(filePath, data) {
        try {
            await fs.writeFile(filePath, JSON.stringify(data, null, 2));
        } catch (error) {
            console.error(`Error writing ${filePath}:`, error);
            throw error;
        }
    }
    
    async getDashboardStats(userId = 'default') {
        try {
            const bills = await this.getBills(userId);
            const transactions = await this.getTransactions(userId);
            
            const pendingBills = bills.filter(b => b.status === 'pending');
            const paidBills = bills.filter(b => b.status === 'paid');
            const totalPending = pendingBills.reduce((sum, b) => sum + b.amount, 0);
            const totalPaid = paidBills.reduce((sum, b) => sum + b.amount, 0);
            
            return {
                totalBills: bills.length,
                pendingBills: pendingBills.length,
                paidBills: paidBills.length,
                totalPendingAmount: totalPending,
                totalPaidAmount: totalPaid,
                recentTransactions: transactions.slice(0, 5)
            };
        } catch (error) {
            console.error('Error getting dashboard stats:', error);
            throw error;
        }
    }
}

module.exports = Database;
