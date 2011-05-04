#!/usr/bin/env python

DESCRIPTION = """
Theory:
   Time-lock puzzles and timed-release Crypto (1996)
   by Ronald L. Rivest, Adi Shamir, and David A. Wagner
"""

from Crypto.Util import randpool
from Crypto.Util import number
from Crypto.Cipher import AES
import sys
import time
import os

try:
    puzzle # placeholder variable
except:
    puzzle = None

SECOND = 1
MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24
MONTH = DAY * 31
YEAR = DAY * 365

MOD_BITS = 1024 # for time-lock puzzle N
SPEED = 75000
SAVE_INTERVAL = SPEED * 30 * MINUTE

AES_BITS = 192

def aes_pad(msg):
    return msg + (16 - len(msg) % 16) * '\0'

def aes_encode(msg, key):
    return AES.new(number.long_to_bytes(key)).encrypt(aes_pad(msg))

def aes_decode(ciphertext, key):
    return AES.new(number.long_to_bytes(key)).decrypt(ciphertext)

# Routine adapted from Anti-Emulation-through-TimeLock-puzzles sample code.
def makepuzzle(t):
    # Init PyCrypto RNG
    rnd = randpool.RandomPool()

    # Generate 512-bit primes
    p = number.getPrime(MOD_BITS/2, rnd.get_bytes)
    q = number.getPrime(MOD_BITS/2, rnd.get_bytes)
    N = p*q
    totient = (p-1)*(q-1)

    key = number.getRandomNumber(AES_BITS, rnd.get_bytes)
    a = number.getRandomNumber(MOD_BITS, rnd.get_bytes) % N

    e = pow(2, t, totient)
    b = pow(a, e, N)

    ck = (key + b) % N
    return (key, {'N': N, 'a': a, 't': t, 'ck': ck})

def eta(remaining, speed):
    seconds = remaining/speed
    if seconds < 100 * SECOND:
        return '%d seconds' % seconds
    elif seconds < 100 * MINUTE:
        return '%d minutes' % (seconds/MINUTE)
    elif seconds < 100 * HOUR:
        return '%d hours' % (seconds/HOUR)
    elif seconds < 60 * DAY:
        return '%d days' % (seconds/DAY)
    elif seconds < 20 * MONTH:
        return '%d months' % (seconds/MONTH)
    else:
        return '%d years' % (seconds/YEAR)

def putestimation(outputstream, puzzle):
    outputstream.write("# Estimated time to solve: %s\n" % eta(puzzle['t'], SPEED))

def save_puzzle(p):
    state = str(p)
    filename = '%d::%d' % (p['ck'] % 1e12, p['t']/SAVE_INTERVAL)
    assert not os.path.exists(filename)
    with open(filename, 'w') as f:
        f.write('# Run ./timelock FILENAME > OUTFILE to decode\n')
        putestimation(f, p)
        f.write('\n')
        f.write(state)
    print >>sys.stderr, "saved state:", filename

def solve_puzzle(p):
    tmp, N, t = p['a'], p['N'], p['t']
    start = time.time()
    for i in xrange(t):
        if (i+1) % SAVE_INTERVAL == 0:
            p2 = p.copy()
            p2['t'] = t-i
            p2['a'] = tmp
            save_puzzle(p2)
        tmp = pow(tmp, 2, N)
        if i % 12345 == 1:
            speed = i/(time.time() - start)
            sys.stderr.write('\r%f squares/s, %d remaining, eta %s        \r'
                % (speed, t-i, eta(t-i, speed)))
    print >>sys.stderr
    return (p['ck'] - tmp) % N

def main():
    if len(sys.argv) <= 1:
        print """Usage: ./timelock.py <PARAM>
Parameters:
    --new [seconds]
    --encrypt <file> [seconds]
    --pack <file> [seconds]
    <saved state> [>outfile]"""
        exit(2)
    if sys.argv[1] == '--new':
        try:
            time = int(sys.argv[2]) * SECOND
        except:
            time = 30 * SECOND
        print "Creating test puzzle with difficulty time %d" % time
        (key, puzzle) = makepuzzle(time*SPEED)
        print "key:", str(key) # Recover the key
        save_puzzle(puzzle)
    elif sys.argv[1] == '--encrypt':
        msg = open(sys.argv[2]).read()
        try:
            time = int(sys.argv[3]) * SECOND
        except:
            time = 30 * SECOND
        (key, puzzle) = makepuzzle(time*SPEED)
        puzzle['ciphertext'] = aes_encode(msg, key)
        save_puzzle(puzzle)
    elif sys.argv[1] == '--pack':
        msg = open(sys.argv[2]).read()
        try:
            time = int(sys.argv[3]) * SECOND
        except:
            time = 30 * SECOND
        (key, puzzle) = makepuzzle(time*SPEED)
        puzzle['ciphertext'] = aes_encode(msg, key)
        print "#!/usr/bin/env python"
        for line in DESCRIPTION.split('\n'):
            print "#", line
        print "# Run this program to recover the original message."
        print "# (scroll down see the program that generated this file)"
        print "#"
        putestimation(sys.stdout, puzzle)
        print "#"
        print
        print "puzzle =", puzzle
        print open(sys.argv[0]).read()
    else:
        try:
            puzzle = eval(open(sys.argv[1]).read())
        except:
            print "Error parsing saved state."
            exit(1)
        solution = solve_puzzle(puzzle)
        print >>sys.stderr, "solution =", solution
        if 'ciphertext' in puzzle:
            print aes_decode(puzzle['ciphertext'], solution)

if __name__ == "__main__":
    if puzzle:
        solution = solve_puzzle(puzzle)
        print >>sys.stderr, "solution =", solution
        if 'ciphertext' in puzzle:
            print aes_decode(puzzle['ciphertext'], solution)
    else:
        main()
