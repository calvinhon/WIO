import 'package:flutter/material.dart';

void main() => runApp(WioApp());

class WioApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WIO Style Credit Card Bills',
      theme: ThemeData(
        primaryColor: Color(0xFF008080), // Teal dark
        scaffoldBackgroundColor: Colors.white,
        textTheme: TextTheme(
          bodyText2: TextStyle(fontFamily: 'Roboto', fontSize: 14, color: Colors.black87),
          headline6: TextStyle(fontWeight: FontWeight.bold, color: Colors.black87),
        ),
      ),
      home: BillTableScreen(),
    );
  }
}

class BillTableScreen extends StatelessWidget {
  final List<Map<String, String>> bills = [
    {
      "bank": "WIO Bank",
      "creditCard": "Visa Platinum",
      "totalDue": "\$1,250.75",
      "minimumPayment": "\$75.00",
      "dueDate": "Aug 15, 2025"
    },
    {
      "bank": "WIO Bank",
      "creditCard": "Mastercard Gold",
      "totalDue": "\$630.40",
      "minimumPayment": "\$40.00",
      "dueDate": "Aug 22, 2025"
    },
    {
      "bank": "WIO Bank",
      "creditCard": "Amex Green",
      "totalDue": "\$980.00",
      "minimumPayment": "\$60.00",
      "dueDate": "Aug 18, 2025"
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Credit Card Bills'),
        backgroundColor: Theme.of(context).primaryColor,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowColor: MaterialStateProperty.all(Color(0xFFE0F2F2)), // Light teal background for header
          columnSpacing: 30,
          columns: [
            DataColumn(label: Text('Bank', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Credit Card', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Total Due', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Minimum Payment', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Due Date', style: TextStyle(fontWeight: FontWeight.bold))),
          ],
          rows: bills
              .map(
                (bill) => DataRow(
                  cells: [
                    DataCell(Text(bill['bank']!)),
                    DataCell(Text(bill['creditCard']!)),
                    DataCell(Text(bill['totalDue']!, style: TextStyle(color: Colors.redAccent))),
                    DataCell(Text(bill['minimumPayment']!, style: TextStyle(color: Colors.orange))),
                    DataCell(Text(bill['dueDate']!)),
                  ],
                ),
              )
              .toList(),
        ),
      ),
    );
  }
}
