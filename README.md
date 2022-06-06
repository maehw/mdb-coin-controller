# mdb-coin-controller
Multidrop bus (MDB) vending machine controller (VMC) for coin acceptor/changer functionality



# Dependencies and execution

Prerequisites: A PC running Python 3, a coin changer (e.g. mei cashflow C7900) with MDB support and a QBIXXX MDB-USB Interface.

Execution:

```
$ python3 MdbCoinController.py -p /dev/ttyACM0
```

Commands are sent according to "Section 5 - Coin Acceptor/Changer VMC/Peripheral Communication Specifications" of the MDB specification.



# Init sequence

- RESET (0x08)

- POLL (0x0B), POLL, ...

- STATUS/SETUP (0x09)

- EXPANSION IDENTIFICATION (0x0F 0x00)

- EXPANSION SEND DIAG STATUS (0x0F 0x05)

- TUBE STATUS (0x0A)

- COIN TYPE (0x0C ...)

# Keep-alive

TODO: use more than one command, e.g.:

* POLL

* EXPANSION SEND DIAG STATUS

# RESET details

Command: RESET (0x08)

Parameters: None

# POLL details

Command: POLL (0x0B)

Parameters: None

Result: needs to be interpreted on a byte-by-byte basis

Note: This is also used for keep-alive of the coin changer.

# STATUS/SETUP details

Command: STATUS/SETUP (0x09)

Parameters: None

Result:

| Byte     | Expected Value  | Meaning                                                      |
| -------- | --------------- | ------------------------------------------------------------ |
| Z1       | 0x03            | Changer Feature Level = Level 3                              |
| Z2..Z3   | 0x1978          | Country / Currency Code: Euro                                |
| Z4       | 0x05            | Coin Scaling Factor<br />(might on the current tube configuration) |
| Z5       | 0x02            | Decimal Places (on a credit display)                         |
| Z6..Z7   | 0x000F = 0b1111 | Indicates what coin types can be routed to the changer’s tubes. |
| Z8       | °0x01           | Coin type #0 credit: 1*Z5, i.e. 5 Euro cents<br />(°depends on the current tube configuration) |
| Z9       | °0x02           | Coin type #1 credit: 2*Z5, i.e. 10 Euro cents                |
| Z10      | °0x04           | Coin type #2 credit: 4*Z5, i.e. 20 Euro cents                |
| Z11      | °0x0A = 10d     | Coin type #3 credit: 10*Z5, i.e. 50 Euro cents               |
| Z12      | °0x14 = 20d     | Coin type #4 credit: 10*Z5, i.e. 1 Euro                      |
| Z13      | °0x28 = 40d     | Coin type #5 credit: 20*Z5, i.e. 2 Euro                      |
| Z14..Z23 | 0x00            | Coin types #6..#15 are not used                              |

# EXPANSION IDENTIFICATION details

Result:

| Byte     | Expected Value                               | Meaning                                                      |
| -------- | -------------------------------------------- | ------------------------------------------------------------ |
| Z1..Z3   | 0x4d4549                                     | Manufacturer Code                                            |
| Z4..Z15  | N/A                                          | 12 byte serial number                                        |
| Z16..Z27 | 0x4346373930304d4442202020<br />="CF7900MDB" | Model #/Tuning Revision (12 bytes)                           |
| Z28..Z29 | 0x0127                                       | BCD Software Version, i.e. "0.1.2.7"                         |
| Z30..Z33 | 0x00000007 = 0b111                           | Optional Features;<br />* Alternative Payout method<br />* Extended Diagnostic command supported<br />* Controlled Manual Fill and Payout commands supported |

# EXPANSION SEND DIAG STATUS details

Result:

| Byte   | Expected Value | Meaning                                                      |
| ------ | -------------- | ------------------------------------------------------------ |
| Z1..Z2 | 0x0300         | Current changer diagnostic information;<br />Z1 is the main code, Z2 is the sub-code<br />0x0300 = OK: Changer fully operational and ready to accept coins |

# TUBE STATUS details

Result:

| Byte    | Expected Value | Meaning                                                      |
| ------- | -------------- | ------------------------------------------------------------ |
| Z1..Z2  | 0x0000         | Tube Full Status (2 byte),<br />a value of 0x0000 would mean that no coin type tube is full |
| Z3..Z18 | N/A            | Tube Status (16 bytes, one byte per coin type). Indicates the greatest number of coins that the changer “knows” definitely are present in the coin tubes. |

# COIN TYPE details

VMC Parameters:

| Byte   | Default Value | Meaning                                                      |
| ------ | ------------- | ------------------------------------------------------------ |
| Y1..Y2 | 0xFFFF        | Coin Enable (2 byte),<br />a value of 0x0000 would disable the acceptance of all coins (as on reset), a value of 0xFFFF accepts all coins |
| Y3..Y4 | 0xFFFF        | Manual Dispense Enbale (2 byte)<br />a value of 0xFFFF (default on reset) enables manual dispensing of all coin types via optional inventory switches! |

Result:

tbc

# DISPENSE details

Command: DISPENSE COIN (0x0D)

VMC Parameters:

| Byte | Default Value | Meaning                                                      |
| ---- | ------------- | ------------------------------------------------------------ |
| Y1.H | 0x1           | High nibble (b7..b4) indicates number of coins to be dispensed (0..15) |
| Y1.L | N/A           | Low nibble (b3..b0) indicates the coin type to be dispensed (0..15) |

Response: X

Additional info: "VMCs should monitor the Changer Payout Busy response to the POLL command to determine when the entire payout cycle is completed."