// server.js
const express = require('express');
const cors = require('cors');
const path = require('path');
const SMSParser = require('./lib/sms-parser');
const Database = require('./lib/database');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Initialize services
const smsParser = new SMSParser();
const database = new Database();

// Connect to database on startup
database.connect().catch(console.error);

// Routes

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Parse SMS messages
app.post('/api/sms/parse', async (req, res) => {
    try {
        const { messages, userId = 'default' } = req.body;
        
        if (!messages || !Array.isArray(messages)) {
            return res.status(400).json({ 
                error: 'Invalid input. Expected array of messages.' 
            });
        }

        const parsedBills = [];
        const errors = [];

        for (const message of messages) {
            try {
                const parsed = smsParser.parseSMS(message.text || message.body, message.sender);
                
                if (parsed) {
                    // Add userId to the parsed result
                    parsed.userId = userId;
                    
                    // Store in database
                    if (parsed.type === 'bill') {
                        await database.storeBill(parsed);
                    } else if (parsed.type === 'payment') {
                        await database.storeTransaction(parsed);
                    }
                    
                    parsedBills.push(parsed);
                } else {
                    console.log(`Could not parse message: ${message.text?.substring(0, 50)}...`);
                }
            } catch (error) {
                console.error('Error processing message:', error);
                errors.push({
                    message: message.text?.substring(0, 50) + '...',
                    error: error.message
                });
            }
        }

        res.json({
            success: true,
            parsed: parsedBills.length,
            total: messages.length,
            bills: parsedBills,
            errors: errors.length > 0 ? errors : undefined
        });

    } catch (error) {
        console.error('Error in SMS parse endpoint:', error);
        res.status(500).json({ 
            error: 'Internal server error',
            details: error.message 
        });
    }
});

// Get all bills
app.get('/api/bills', async (req, res) => {
    try {
        const { userId = 'default', status, bank } = req.query;
        const filter = {};
        
        if (status) filter.status = status;
        if (bank) filter.bank = bank;
        
        const bills = await database.getBills(userId, filter);
        
        res.json({
            success: true,
            count: bills.length,
            bills: bills
        });
    } catch (error) {
        console.error('Error fetching bills:', error);
        res.status(500).json({ 
            error: 'Failed to fetch bills',
            details: error.message 
        });
    }
});

// Update bill status
app.put('/api/bills/:billId/status', async (req, res) => {
    try {
        const { billId } = req.params;
        const { status } = req.body;
        
        if (!['pending', 'paid', 'overdue'].includes(status)) {
            return res.status(400).json({ 
                error: 'Invalid status. Must be: pending, paid, or overdue' 
            });
        }
        
        const updated = await database.updateBillStatus(billId, status);
        
        if (updated) {
            res.json({ success: true, message: 'Bill status updated' });
        } else {
            res.status(404).json({ error: 'Bill not found' });
        }
    } catch (error) {
        console.error('Error updating bill status:', error);
        res.status(500).json({ 
            error: 'Failed to update bill status',
            details: error.message 
        });
    }
});

// Get transactions
app.get('/api/transactions', async (req, res) => {
    try {
        const { userId = 'default', type } = req.query;
        const filter = {};
        
        if (type) filter.type = type;
        
        const transactions = await database.getTransactions(userId, filter);
        
        res.json({
            success: true,
            count: transactions.length,
            transactions: transactions
        });
    } catch (error) {
        console.error('Error fetching transactions:', error);
        res.status(500).json({ 
            error: 'Failed to fetch transactions',
            details: error.message 
        });
    }
});

// Dashboard stats
app.get('/api/dashboard', async (req, res) => {
    try {
        const { userId = 'default' } = req.query;
        const stats = await database.getDashboardStats(userId);
        
        res.json({
            success: true,
            stats: stats
        });
    } catch (error) {
        console.error('Error fetching dashboard stats:', error);
        res.status(500).json({ 
            error: 'Failed to fetch dashboard stats',
            details: error.message 
        });
    }
});

// Test endpoint with sample data
app.post('/api/test', async (req, res) => {
    try {
        const sampleMessages = [
            {
                text: "HDFC Bank: Your credit card bill of Rs.15,000 is due on 15/01/2024. Please pay before the due date to avoid late fees.",
                sender: "HDFC-BANK"
            },
            {
                text: "SBI Card: Minimum amount due Rs.5,500 on your card ending 1234. Due date: 20/01/2024. Pay now to avoid charges.",
                sender: "SBI-CARD"
            },
            {
                text: "Payment successful! Rs.15,000 has been debited from your account for HDFC credit card bill payment.",
                sender: "HDFC-BANK"
            },
            {
                text: "ICICI Bank: Your credit card statement is ready. Total amount due: Rs.8,750. Due date: 18/01/2024.",
                sender: "ICICI-BANK"
            }
        ];

        const { userId = 'test-user' } = req.body;
        const parsedBills = [];

        for (const message of sampleMessages) {
            const parsed = smsParser.parseSMS(message.text, message.sender);
            
            if (parsed) {
                parsed.userId = userId;
                
                if (parsed.type === 'bill') {
                    await database.storeBill(parsed);
                } else if (parsed.type === 'payment') {
                    await database.storeTransaction(parsed);
                }
                
                parsedBills.push(parsed);
            }
        }

        res.json({
            success: true,
            message: 'Test data processed successfully',
            parsed: parsedBills.length,
            bills: parsedBills
        });

    } catch (error) {
        console.error('Error in test endpoint:', error);
        res.status(500).json({ 
            error: 'Test failed',
            details: error.message 
        });
    }
});

// Serve the dashboard
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'dashboard.html'));
});

// Error handler
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ 
        error: 'Something broke!',
        details: err.message 
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down gracefully');
    await database.disconnect();
    process.exit(0);
});

process.on('SIGINT', async () => {
    console.log('SIGINT received, shutting down gracefully');
    await database.disconnect();
    process.exit(0);
});

// Start server
app.listen(PORT, () => {
    console.log(`✅ Credit Card Assistant API running on port ${PORT}`);
    console.log(`🌐 Dashboard: http://localhost:${PORT}`);
    console.log(`📱 API: http://localhost:${PORT}/api`);
    console.log(`🏥 Health Check: http://localhost:${PORT}/health`);
});

module.exports = app;