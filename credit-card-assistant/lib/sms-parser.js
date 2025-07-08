class SMSParser {
    constructor() {
        // Bank-specific patterns for credit card bills
        const currency = '(?:AED|Rs\.?)(?:\s*)';

        this.bankPatterns = {
            'HDFC': new RegExp(`HDFC.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'SBI': new RegExp(`SBI.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'ICICI': new RegExp(`ICICI.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'AXIS': new RegExp(`AXIS.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'KOTAK': new RegExp(`KOTAK.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'CITI': new RegExp(`CITI.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'AMERICAN EXPRESS': new RegExp(`AMEX.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),

            // UAE banks
            'WIO': new RegExp(`WIO.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'ADCB': new RegExp(`ADCB.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'FAB': new RegExp(`FAB.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'DIB': new RegExp(`DIB.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'ACB': new RegExp(`ACB.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'EIB': new RegExp(`EIB.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i'),
            'ENBD': new RegExp(`ENBD.*(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i')
        };

        this.paymentPatterns = [
            /payment.*(?:successful|completed|processed).*?(?:AED|Rs\.?)(\d+(?:,\d{3})*(?:\.\d{2})?)/i,
            /was.*(?:successful|processed).*?(?:AED|Rs\.?)(\d+(?:,\d{3})*(?:\.\d{2})?)/i,
            /credited.*?(?:AED|Rs\.?)(\d+(?:,\d{3})*(?:\.\d{2})?)/i,
            /debited.*?(?:AED|Rs\.?)(\d+(?:,\d{3})*(?:\.\d{2})?)/i
        ];

        this.transactionPatterns = [
            /(?:used for|charged|spent|debited|purchased).*(?:AED|Rs\.?)(\d+(?:,\d{3})*(?:\.\d{2})?)/i
        ];

        this.genericBillPattern = new RegExp(`(?:bill|due|payment).*${currency}(\d+(?:,\d{3})*(?:\.\d{2})?).*?(?:due|by).*?(\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4})`, 'i');
    }

    parseSMS(smsText, sender = '') {
        console.log(`Parsing SMS from ${sender}: ${smsText.substring(0, 100)}...`);

        for (const [bank, pattern] of Object.entries(this.bankPatterns)) {
            const matches = smsText.match(pattern);
            if (matches) {
                console.log(`Matched ${bank} pattern`);
                return {
                    id: this.generateId(),
                    bank,
                    amount: this.parseAmount(matches[1]),
                    dueDate: this.normalizeDateFormat(matches[2]),
                    type: 'bill',
                    rawMessage: smsText,
                    sender,
                    status: 'pending',
                    confidence: 0.95,
                    parsedAt: new Date().toISOString()
                };
            }
        }

        for (const pattern of this.paymentPatterns) {
            const matches = smsText.match(pattern);
            if (matches) {
                console.log('Matched payment pattern');
                return {
                    id: this.generateId(),
                    bank: this.extractBankFromSender(sender),
                    amount: this.parseAmount(matches[1]),
                    type: 'payment',
                    rawMessage: smsText,
                    sender,
                    status: 'completed',
                    confidence: 0.90,
                    parsedAt: new Date().toISOString()
                };
            }
        }

        for (const pattern of this.transactionPatterns) {
            const matches = smsText.match(pattern);
            if (matches) {
                console.log('Matched transaction pattern');
                return {
                    id: this.generateId(),
                    bank: this.extractBankFromSender(sender),
                    amount: this.parseAmount(matches[1]),
                    type: 'transaction',
                    rawMessage: smsText,
                    sender,
                    status: 'noted',
                    confidence: 0.85,
                    parsedAt: new Date().toISOString()
                };
            }
        }

        const genericMatch = smsText.match(this.genericBillPattern);
        if (genericMatch) {
            console.log('Matched generic bill pattern');
            return {
                id: this.generateId(),
                bank: this.extractBankFromSender(sender) || 'UNKNOWN',
                amount: this.parseAmount(genericMatch[1]),
                dueDate: this.normalizeDateFormat(genericMatch[2]),
                type: 'bill',
                rawMessage: smsText,
                sender,
                status: 'pending',
                confidence: 0.70,
                parsedAt: new Date().toISOString()
            };
        }

        console.log('No pattern matched');
        return null;
    }

    parseAmount(amountStr) {
        if (!amountStr) return 0;
        return parseFloat(amountStr.replace(/,/g, '').replace(/[^\d.]/g, '')) || 0;
    }

monthNameToNumber(monthStr) {
    const months = {
        Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06',
        Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12'
    };
    return months[monthStr.slice(0, 3).toLowerCase().replace(/^\w/, c => c.toUpperCase())] || '01';
}


normalizeDateFormat(dateStr) {
    if (!dateStr) return null;

    const formats = [
        /(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})/,
        /(\d{1,2})[ ]?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[ ]?[-,]?[ ]?(\d{2,4})/i
    ];
    
    for (const format of formats) {
        const match = dateStr.match(format);
        if (match) {
            // Convert to YYYY-MM-DD
            let day, month, year;

            if (match.length === 4 && isNaN(match[2])) {
                // Format: 07 Jul 2025
                [ , day, month, year ] = match;
                month = this.monthNameToNumber(month);
            } else {
                [ , day, month, year ] = match;
            }

            if (year.length === 2) year = parseInt(year) > 30 ? `19${year}` : `20${year}`;
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        }
    }

    return dateStr;
}


    extractBankFromSender(sender) {
        const bankCodes = {
            'HDFC': 'HDFC', 'SBI': 'SBI', 'ICICI': 'ICICI', 'AXIS': 'AXIS',
            'KOTAK': 'KOTAK', 'CITI': 'CITI', 'AMEX': 'AMERICAN EXPRESS',
            'ENBD': 'ENBD', 'WIO': 'WIO', 'ADCB': 'ADCB', 'FAB': 'FAB',
            'DIB': 'DIB', 'ACB': 'ACB', 'EIB': 'EIB', 'RAKBANK': 'RAKBANK'
        };

        const upperSender = sender.toUpperCase();
        for (const [code, name] of Object.entries(bankCodes)) {
            if (upperSender.includes(code)) return name;
        }

        return null;
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substring(2);
    }
}

module.exports = SMSParser;
