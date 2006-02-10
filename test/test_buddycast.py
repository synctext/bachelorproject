import os
import unittest
import tempfile
from sets import Set
from traceback import print_exc

from BitTornado.bencode import bencode, bdecode
from Tribler.BuddyCast.buddycast2 import *
from Tribler.CacheDB.cachedb import *
from Tribler.utilities import print_prefxchg_msg
import Tribler.CacheDB.superpeer

import hotshot, hotshot.stats
import math



testdata_file = 'test/testdata.txt'
myid = 147

class TestBuddyCast(unittest.TestCase):
    """ 
    Testing buddycast includes two steps:
        1. Test buddycast algorithm
        2. Test buddycast communication functionalities
    Here we can only test step 1.
    """
    
    def setUp(self):
        self.tmpdirpath = db_dir = os.path.join(tempfile.gettempdir(), 'testdb')
        self.buddycast = BuddyCastFactory.getInstance(db_dir=self.tmpdirpath)
        self.buddycast.data_handler.clear()
        
        testdata = open(testdata_file, 'r')
        self.prefxchg_msgs = testdata.readlines()
        testdata.close()
        self.np = len(self.prefxchg_msgs)
        self.myid = myid
        msg = self.prefxchg_msgs[self.myid-1].strip()
        self.mydata = bdecode(msg)
        self.prefs = self.mydata['preferences']
        self.buddycast.ip = self.mydata['ip']
        self.buddycast.port = self.mydata['port']
        self.buddycast.permid = self.mydata['permid']
        self.buddycast.name = self.mydata['name']
        for p in self.prefs:
            self.buddycast.addMyPref(p)
                
        self.my_db = MyDB.getInstance(db_dir=db_dir)
        self.peer_db = PeerDB.getInstance(db_dir=db_dir)
        self.torrent_db = TorrentDB.getInstance(db_dir=db_dir)
        self.mypref_db = MyPreferenceDB.getInstance(db_dir=db_dir)
        self.pref_db = PreferenceDB.getInstance(db_dir=db_dir)
        self.owner_db = OwnerDB.getInstance(db_dir=db_dir)    
        #Tribler.CacheDB.superpeer.init()
        #print self.my_db._data
        
#        for pref in self.prefs:
#            self.mypref_db.updateItem(pref)
        
    def tearDown(self):
        self.buddycast.data_handler.clear()
        
    def full_load(self):
        for i in xrange(self.np):
            if i == self.myid:
                continue
            msg = self.prefxchg_msgs[i].strip()
            self.buddycast.gotBuddyCastMsg(msg)
            if i%10 == 0:
                print i, self.peer_db._size(), self.torrent_db._size(), self.pref_db._size()
        
    def preload(self):
        for i in xrange(136,156):    #self.np
            if i == self.myid:
                continue
            msg = self.prefxchg_msgs[i].strip()
            self.buddycast.gotBuddyCastMsg(msg)
        assert self.peer_db._size() == 309 , self.peer_db._size()
        assert self.torrent_db._size() == 919
        assert self.pref_db._size() == 160
        assert self.torrent_db._size() == self.owner_db._size()
        
    def preload2(self, begin=136, num=10):
        end = begin + num
        for i in xrange(begin,end):    #self.np
            if i == self.myid:
                continue
            msg = self.prefxchg_msgs[i].strip()
            self.buddycast.gotBuddyCastMsg(msg)
        #print self.peer_db._size(), self.torrent_db._size(), self.pref_db._size()
        
    def test_updateDB(self):
        msg = self.prefxchg_msgs[0].strip()
        self.buddycast.gotBuddyCastMsg(msg)
        assert self.peer_db._size() == 21, self.peer_db._data.keys()
        assert self.torrent_db._size() == 132, self.torrent_db._size()
        assert self.pref_db._size() == 11, self.pref_db._size()
        assert self.owner_db._size() == 132, self.owner_db._size()
        assert self.mypref_db._size() == 50, self.mypref_db._size()

    def test_createWorker(self):
        self.preload()
        worker = self.buddycast.createWorker('peer 0')
        buddycast_data = worker.getBuddyCastMsgData()
        try:
            validBuddyCastData(buddycast_data)
            msg = bencode(buddycast_data)
        except:
            print_exc()
            print_dict(buddycast_data)
            print >> sys.stderr, "bad buddycast data", buddycast_data
        #print_prefxchg_msg(buddycast_data)
        #print_dict(buddycast_data)
        #print len(msg), hash(msg)
        #worker.work()
        
    def test_getMsgTBPeers(self):
        self.preload()
        target, tbs, rps = self.buddycast.data_handler.getBuddyCastData('peer 0', 10, 10)
        assert target == 'peer 0' and len(tbs) == 10 and len(rps) == 10
        
    def test_WorkerQueue(self):
        q = WorkerQueue(None, max_size=5)
        q.addWorker('worker1')
        assert q._queue == ['worker1']
        q.addWorker(['worker2', 'worker3'])
        assert q._queue == ['worker1', 'worker2', 'worker3']
        q.addWorker(['worker44', 'worker55', 'worker66'], 0)
        assert q._queue == ['worker1', 'worker2', 'worker3', 'worker44', 'worker55']
        q.addWorker(['worker4', 'worker5', 'worker6'], 1)
        assert q._queue == ['worker4', 'worker5', 'worker6', 'worker1', 'worker2']
        assert q.getWorker() == 'worker4'
        assert q._queue == ['worker5', 'worker6', 'worker1', 'worker2']
        

    def xxtest_getBuddyCastDataPref(self):
        """ result:
            time  #peer, #taste buddies
            0.016 182 96
            0.015 309 160
            0.047 426 230
            0.046 533 295
            0.062 604 350
            0.062 666 390
            0.062 719 418
            0.078 767 460
            0.078 807 495
            0.094 837 524
            0.094 870 558
            0.092 888 576
            0.094 905 592
            0.094 921 618
            0.094 935 635
            0.109 946 655
            0.110 965 675
            0.110 970 694
            0.108 977 717
            0.125 981 738
        """
        for i in range(20):
            self.preload2(136+i*10, 10)
            begin = time()
            target, tbs, rps = self.buddycast.data_handler.getBuddyCastData(None, 10, 10)
            print time() - begin, self.peer_db._size(), self.pref_db._size()
            
    def xxtest_profile(self):
        def foo(n = 10000):
            def bar(n):
                for i in range(n):
                    math.pow(i,2)
            def baz(n):
                for i in range(n):
                    math.sqrt(i)
            bar(n)
            baz(n)
        
        self.preload2(136, 30)
        print "profile starts"
        prof = hotshot.Profile("test.prof")
        prof.runcall(self.buddycast.data_handler.getBuddyCastData)
        prof.close()
        stats = hotshot.stats.load("test.prof")
        stats.strip_dirs()
        stats.sort_stats('cumulative', 'time', 'calls')
        stats.print_stats(100)
        
    def test_addMyPref(self):
        self.preload()
        items = self.owner_db._items()
#        for item in items:
#            if len(item[1]) > 7 and not self.mypref_db._has_key(item[0]):
#                print item[0], len(item[1]), item[1]
        new_item = '1651'
#        for p, v in self.peer_db._items():
#            print p, v['similarity']
        assert self.peer_db.getItem('peer_145')['similarity'] == 100
        assert self.peer_db.getItem('peer_83')['similarity'] == 0
        assert self.peer_db.getItem('peer_509')['similarity'] == 134
        owners = self.owner_db.getItem(new_item)
#        for o in owners:
#            print o, self.peer_db.getItem(o)
#        print p, self.peer_db.getItem('peer_509')
        self.buddycast.addMyPref(new_item)
        assert self.peer_db.getItem('peer_145')['similarity'] == 118
        assert self.peer_db.getItem('peer_83')['similarity'] == 44
        assert self.peer_db.getItem('peer_509')['similarity'] == 132
#        print
#        for o in owners:
#            print o, self.peer_db.getItem(o)
#        print p, self.peer_db.getItem('peer_509')
    
#    def test_selectBuddyCastCandidate(self):
#        pass
    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBuddyCast))
    
    return suite

    