import argparse
import serial
import sys
import math
import time

class MdbCoinController:
    ser = None
    validSerialDev = False
    ct_values = [] # values for all the coin types
    balance = 0
    token_cost = 50

    def __init__(self, serport, verbose=True):
        self.ct_values = []
        self.balance = 0

        # initialize serial device, the MDB interface and also the coin changer (connected via the MDB interface)
        if serport is not False:
            try:
                self.ser = serial.Serial(serport, 115200, timeout=2, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=1, xonxoff=0, rtscts=0)
                self.validSerialDev = True
            except serial.serialutil.SerialException:
                if verbose:
                    print(r"[DEBUG] Serial device is not available." )
                raise ValueError('Serial device is not available.')

            if self.validSerialDev and verbose:
                    print(r"[DEBUG] Serial device port name: '{}'".format(self.ser.name) )

            if self.readversion():
                if verbose:
                    print("[INFO] Version readout succeeded.")
            else:
                print("[ERROR] Version readout failed.")
                return None
                
            if self.setmastermode():
                if verbose:
                    print("[INFO] Setting master mode succeeded.")
            else:
                print("[ERROR] Setting master mode failed.")
                return None

            if self.coinchanger_reset():
                if verbose:
                    print("[INFO] Reset of coin changer succeeded.")
            else:
                print("[ERROR] Reset of coin changer failed.")
                return None

            # poll several times until we get an ACK
            for a in range(1,1+10):
                resp = self.coinchanger_poll()
                if resp == True:
                    if verbose:
                        print("[INFO] Poll only got ACK.")
                        break
                elif resp:
                    if verbose:
                        print("[INFO] Poll of coin changer succeeded.")
                else:
                    print("[ERROR] Poll of coin changer failed finally.")
                    return None

            if self.coinchanger_setup():
                if verbose:
                    print("[INFO] Setup of coin changer succeeded.")
            else:
                print("[ERROR] Setup of coin changer failed.")
                return None

            if self.coinchanger_identify():
                if verbose:
                    print("[INFO] Coin changer identification command succeeded.")
            else:
                print("[ERROR] Coin changer identification command failed.")
                return None

            if self.coinchanger_diagnose():
                if verbose:
                    print("[INFO] Coin changer diagnosis command succeeded.")
            else:
                print("[ERROR] Coin changer diagnosis command failed.")
                return None

            if self.coinchanger_reqtubestatus():
                if verbose:
                    print("[INFO] Request of tube status succeeded.")
            else:
                print("[ERROR] Request of tube status failed.")
                return None

            if self.coinchanger_cointype():
                if verbose:
                    print("[INFO] Coin type command succeeded.")
            else:
                print("[ERROR] Coin type command failed.")
                return None

            self.loop()

    def loop(self):
        # TODO: implement loop for processing, i.e. poll, process accepted coints, dispense token when credit is high enough, give change, handle errors
        print("[DEBUG] Poll endlessly................")
        while True:
            resp = self.coinchanger_poll()
            if resp == True:
                if verbose:
                    #print("[INFO] Poll only got ACK.")
                    pass
            elif resp:
                if verbose:
                    #print("[INFO] Poll of coin changer succeeded.")
                    pass
            else:
                print("[ERROR] Poll of coin changer failed.")
                return None
            time.sleep( 0.5 )

    def readline(self, verbose=False):
        '''Read a line from the serial'''
        
        if not self.validSerialDev:
            print( r"[ERROR] No valid serial device." )
            return False

        line = self.ser.readline()
        if verbose:
            print(r"[INFO] Read from serial: {}".format(line) )

        line = line.decode("ascii").rstrip()

        if verbose:
            print(r"[INFO] Read from serial (stripped): {}".format(line) )

        return line

    def writeline(self, line, verbose=False):
        '''Transmit a line from serial byte per byte'''
        
        if not self.validSerialDev:
            print( r"[ERROR] No valid serial device." )
            return False

        if verbose:
            print(r"[INFO] Write to serial: {}".format(line) )

        for k in range(0, len(line)):
            cTx = line[k].to_bytes(1, byteorder='big')
            self.ser.write(cTx)
        return True

    def sendcmd(self, cmd, verbose=True):

        if not self.validSerialDev:
            print( "[ERROR] No valid serial device." )
            return False

        if not self.writeline(line=cmd):
            print( "[ERROR] Tx on serial device failed." )
            return False

        rx = self.readline()
        #print(r"[DEBUG] Rx from serial: {}".format(rx) )

        if not rx:
            print( "[ERROR] Rx on serial device failed." )
            return False
        
        if "NACK" in rx:
            print( "[ERROR] Rx'ed NACK." )
            return False
 
        return rx

    def readversion(self, verbose=True):

        resp = self.sendcmd( b'V\n' )
        #print( r"[DEBUG] Response: {}.".format( resp ) )
        if not resp:
            return False

        return resp.startswith( "v," )

    def setmastermode(self, verbose=True):

        resp = self.sendcmd( b'M,1\n' )
        print( r"[DEBUG] Response: {}.".format( resp ) )
        if not resp:
            return False
            
        if not "m,ACK" in resp:
            print( "[ERROR] No ACK." )
            return False

        return True

    def coinchanger_reset(self, verbose=True):

        resp = self.sendcmd( b'R,08\n' )
        print( r"[DEBUG] Response: {}.".format( resp ) )
        if not resp:
            return False
 
        return True

    def coinchanger_poll(self, verbose=True):

        response = self.sendcmd( b'R,0B\n' )
        #print( r"[DEBUG]   Response: {}.".format( response ) )
        if not response:
            return False

        resp = response[2:] # expected length of binary result: up to 16 bytes
        #print( r"[DEBUG]   Response (stripped): {}.".format( resp ) )
        
        if "ACK" in resp:
            #print( "[DEBUG] ACK." )
            return True
        
        # get next byte
        z1_hexstr = resp[0:2]
        z1_dec = int(z1_hexstr, 16)
        print( r"[DEBUG]   Response byte: 0x{} / {} decimal.".format( z1_hexstr, z1_dec ) )

        if z1_dec == 0:
            print( "[ERROR] Invalid (at least unexpected) response byte." )
            return False

        # try to find most significant bit that is set
        z1_msbitpos = int( round(math.log(z1_dec, 2)) )
        print( r"[DEBUG]   Position of MSBit set: {}.".format( z1_msbitpos ) )
        
        if z1_msbitpos == 7:
            print( r"[DEBUG]   Activity: Coins Dispensed Manually" )
            # Z1 = 0b1yyyxxxx, Z2 = 0bzzzzzzzz:
            #         yyy:                      number of coins dispensed
            #            xxxx:                  coin type deposited
            #                         zzzzzzzz: number of coins *in the tube* for the coin type accepted
            num_coins = (z1_dec & 0x70) >> 4
            coin_type = (z1_dec & 0x0F)
            res_value = self.ct_values[coin_type]*num_coins # resulting value for all coins
            print( r"[DEBUG]     Coin type: {}".format(coin_type) )
            print( r"[DEBUG]     Number of dispensed coins: {}".format(num_coins) )
            print( r"[DEBUG]     Resulting value of dispensed coins: {}".format(res_value) )

            z2_hexstr = resp[2:4]
            z2_dec = int(z2_hexstr, 16)
            print( r"[DEBUG]     Second response byte: 0x{} / {} decimal.".format( z2_hexstr, z2_dec ) )

            num_coins_tube = z2_dec
            print( r"[DEBUG]     Number of coins in the tube of this type: {}".format(num_coins_tube) )

            self.change_balance( -res_value )

        elif z1_msbitpos == 6:
            print( r"[DEBUG]   Activity: Coins Deposited" )
            # Z1 = 0b01yyxxxx, Z2 = 0bzzzzzzzz:
            #          yy:                      coin routing
            #            xxxx:                  coin type deposited
            #                         zzzzzzzz: number of coins *in the tube* for the coin type accepted
            coin_routing = (z1_dec & 0x30) >> 4
            coin_type = (z1_dec & 0x0F)

            z2_hexstr = resp[2:4]
            z2_dec = int(z2_hexstr, 16)
            print( r"[DEBUG]     Second response byte: 0x{} / {} decimal.".format( z2_hexstr, z2_dec ) )

            num_coins_tube = z2_dec
            print( r"[DEBUG]     Coin type: {}".format(coin_type) )
            print( r"[DEBUG]     Number of coins in the tube of this type: {}".format(num_coins_tube) )

            res_value = self.ct_values[coin_type] # resulting value for all coins
            # TODO: assure that only a single coin has been deposited!
            print( r"[DEBUG]     Value of coin: {}".format(res_value) )

            print( r"[DEBUG]     Coin routing: {}".format(coin_routing) )
            if coin_routing == 0:
                print( r"[DEBUG]     Coin routing: routed to CASH BOX" )
                self.change_balance( +res_value )
            elif coin_routing == 1:
                print( r"[DEBUG]     Coin routing: routed to TUBES" )
                self.change_balance( +res_value )
            elif coin_routing == 2:
                print( r"[DEBUG]     Coin routing: routed to NOT USED" )
                return False
            elif coin_routing == 3:
                print( r"[DEBUG]     Coin routing: routed to REJECT" )
            else:
                print( r"[DEBUG]     Coin routing: unexpected value: {}".format( coin_routing) )
                return False

        elif z1_msbitpos == 5:
            print( r"[DEBUG]   Activity: Slug" )
        elif z1_msbitpos <= 4:
            print( r"[DEBUG]   Activity: Status" )
            if z1_dec == 1:
                print( r"[DEBUG]             Escrow request - An escrow lever activation has been detected" )
                # TODO: pay out current balance from the tubes
            elif z1_dec == 2:
                print( r"[DEBUG]             Changer Payout Busy - The changer is busy activating payout devices" )
            elif z1_dec == 3:
                print( r"[DEBUG]             No Credit - A coin was validated but did not get to the place in the system when credit is given" )
            elif z1_dec == 4:
                print( r"[DEBUG]             Defective Tube Sensor - The changer has detected one of the tube sensors behaving abnormally" )
            elif z1_dec == 5:
                print( r"[DEBUG]             Double Arrival - Two coins were detected too close together to validate either one" )
            elif z1_dec == 6:
                print( r"[DEBUG]             Acceptor Unplugged - The changer has detected that the acceptor has been removed" )
            elif z1_dec == 7:
                print( r"[DEBUG]             Tube Jam - A tube payout attempt has resulted in jammed condition" )
            elif z1_dec == 8:
                print( r"[DEBUG]             ROM checksum error - The changers internal checksum does not match the calculated checksum" )
            elif z1_dec == 9:
                print( r"[DEBUG]             Coin Routing Error - A coin has been validated, but did not follow the intended routing" )
            elif z1_dec == 10:
                print( r"[DEBUG]             Changer Busy - The changer is busy and can not answer a detailed command right now" )
                time.sleep( 1 )
            elif z1_dec == 11:
                print( r"[DEBUG]             Changer was Reset - The changer has detected an Reset condition and has returned to its power-on idle condition" )
                time.sleep( 1 )
            elif z1_dec == 12:
                print( r"[DEBUG]             Coin Jam - A coin(s) has jammed in the acceptance path" )
                time.sleep( 1 )
            elif z1_dec == 13:
                print( r"[DEBUG]             Possible Credited Coin Removal – There has been an attempt to remove a credited coin" )
            else:
                print( r"[DEBUG]             !!! Unknown or unhandled status !!!" )

        return response

    def coinchanger_setup(self, verbose=True):

        response = self.sendcmd( b'R,09\n' )
        print( r"[DEBUG] Response: {}.".format( response ) )
        if not response:
            return False

        resp = response[2:] # expected length of binary result: 23 bytes, i.e. 46 nibbles

        feat_level = int(resp[0:2], 16)
        cc_curr = resp[2:6]
        cs_fac = int(resp[6:8], 16)
        dec_places = int(resp[8:10], 16)
        ct_routing = resp[10:14]
        
        print( r"[DEBUG]   Feature level: {}".format( feat_level ) )
        print( r"[DEBUG]   Currency/ country code: 0x{}".format( cc_curr ) )
        print( r"[DEBUG]   Coin scaling factor: {}".format( cs_fac ) )
        print( r"[DEBUG]   Decimal places: {}".format( dec_places ) )
        print( r"[DEBUG]   Coin type routing: 0x{}".format( ct_routing ) )

        start_offset = 14
        for coin_type in range(16):
            ct_value = int(resp[start_offset + coin_type*2 : start_offset + (coin_type+1)*2], 16) * cs_fac
            #print( r"[DEBUG]   Coin type #{}'s credit value: {}".format(coin_type, ct_value) )
            self.ct_values.append( ct_value )

        print( r"[DEBUG]   Coin type credit values: {}".format( self.ct_values ) )
        
        return True

    def coinchanger_reqtubestatus(self, verbose=True):

        response = self.sendcmd( b'R,0A\n' )
        print( r"[DEBUG] Response: {}.".format( response ) )
        if not response:
            return False

        resp = response[2:] # expected length of binary result: 18 bytes, i.e. 36 nibbles

        fullstat = resp[0:4]
        stat = resp[4:36]
        coin0_stat = int( stat[0:2], 16 )
        coin1_stat = int( stat[2:4], 16 )
        coin2_stat = int( stat[4:6], 16 )
        coin3_stat = int( stat[6:8], 16 )
 
        print( r"[DEBUG]   Tube Full Status: 0x{}.".format( fullstat ) )
        print( r"[DEBUG]   Tube Status: coin0:{}, coin1:{}, coin2:{}, coin3:{}".format( coin0_stat, coin1_stat, coin2_stat, coin3_stat ) )
        # TODO/FIXME: detect and signal tube malfunction!

        return True

    def coinchanger_cointype(self, verbose=True):

        resp = self.sendcmd( b'R,0C,FFFFFFFF\n' ) # TODO: add parameters; current setting accepts all coin types and enabled manual dispensing for all
        print( r"[DEBUG] Response: {}.".format( resp ) )
        if not resp:
            return False
 
        return True

    def coinchanger_dispense_token(self, verbose=True):

        # this method is based on the 'dispense coin' feature, however there's a token in the tube, not a coin!
        resp = self.sendcmd( b'R,0D,13\n' ) # TODO: add parameters; current setting dispenses a single coin (high nibble) of type #3 (low nibble)!
        print( r"[DEBUG] Response: {}.".format( resp ) )
        if not resp:
            return False
 
        return True

    def coinchanger_identify(self, verbose=True):

        response = self.sendcmd( b'R,0F,00\n' )
        print( r"[DEBUG] Response: {}.".format( response ) )
        if not response:
            return False
 
        resp = response[2:] # expected length of binary result: 33 bytes, i.e. 66 nibbles

        manufac = bytes.fromhex( resp[0:6] ).decode('ascii')
        serialno = bytes.fromhex( resp[6:30] ).decode('ascii')
        modelrev = bytes.fromhex( resp[30:54] ).decode('ascii')
        swversion = resp[54:58]
        opt_feats = resp[58:66]

        print( r"[DEBUG]   Manufacturer Code: {}".format( manufac ) )
        print( r"[DEBUG]   Serial Number: {}".format( serialno ) )
        print( r"[DEBUG]   Model #/Tuning Revision: {}".format( modelrev ) )
        print( r"[DEBUG]   Software Version: {}".format( swversion ) )
        print( r"[DEBUG]   Optional Features: 0x{}".format( opt_feats ) )

        return True

    def coinchanger_diagnose(self, verbose=True):

        print( r"[DEBUG] coinchanger_diagnose()" )
        response = self.sendcmd( b'R,0F,05\n' )
        print( r"[DEBUG] Response: {}.".format( response ) )
        if not response:
            print( r"[ERROR] Did not get a valid response." )
            return False

        resp = response[2:]

        maincode = resp[0:2]
        subcode = resp[2:4]
        print( r"[DEBUG] Codes: maincode=0x{} subcode=0x{}.".format(maincode, subcode) )

        # 0x0300 = OK: Changer fully operational and ready to accept coins
        #if not "r,0300" in response:
        #    print( r"[DEBUG] Did not find 0300." )
        #    return False
        # TODO/FIXME: add error logging and handling
 
        return True

    def change_balance(self, value=0):
        print( r"[DEBUG] Balance before change: {}".format( self.balance ) )
        self.balance += value
        print( r"[DEBUG] Balance after change: {}".format( self.balance ) )
        
        if value > 0: # if value has been added check if it is enough to buy a token
            if self.balance >= self.token_cost:
                # try to dispense a token
                if self.coinchanger_dispense_token(): # change balance on success
                    self.change_balance( -self.token_cost )
                    print( r"[INFO] RELEASED A TOKEN!" )
                else:
                    pass # TODO: add retries!

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='%(prog)s')

    parser.add_argument('-p', action="store", default=False, 
                    dest='serport',
                    help="serial device port name (e.g. '/dev/ttyUSB0' or 'COM1')")

    parser.add_argument('-v', action="store", default=False,
                    dest='verbosity',
                    help='print detailed output')

    args = parser.parse_args()

    print(args) # for debugging purpose
    
    verbose = True

    if not args.serport:
        print( "[ERROR] A serial port (-p) needs to be provided." )
        sys.exit(1)

    inst = MdbCoinController(serport=args.serport, verbose=verbose)

    sys.exit(0)
