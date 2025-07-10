import 'package:flutter/material.dart';

class DashboardScreen extends StatelessWidget {
  final List<Map<String, String>> bills = const [
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

  const DashboardScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Credit Card Bills'),
        backgroundColor: const Color(0xFF6932F0),
        elevation: 0,
      ),
      body: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowColor: MaterialStateProperty.all(const Color(0xFFF2F2F2)),
          columnSpacing: 30,
          columns: const [
            DataColumn(label: Text('Bank', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Credit Card', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Total Due', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Minimum Payment', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Due Date', style: TextStyle(fontWeight: FontWeight.bold))),
            DataColumn(label: Text('Status', style: TextStyle(fontWeight: FontWeight.bold))),
          ],
          rows: bills
              .map(
                (bill) => DataRow(
                  cells: [
                    DataCell(Text(bill['bank']!)),
                    DataCell(Text(bill['creditCard']!)),
                    DataCell(Text(
                      bill['totalDue']!,
                      style: const TextStyle(color: Color(0xFF6932F0), fontWeight: FontWeight.bold),
                    )),
                    DataCell(Text(
                      bill['minimumPayment']!,
                      style: const TextStyle(color: Colors.orange),
                    )),
                    DataCell(Text(bill['dueDate']!)),
                    DataCell(Text('Not paid', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold))),
                  ],
                ),
              )
              .toList(),
        ),
      ),
    );
  }
}
