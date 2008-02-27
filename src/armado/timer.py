import time
class Timer:
    def start(self, total):
        self.start_time = self.last_tick = time.time()
        self.total = total
        self.done = 0
        
    def tick(self, amount=1):
        now = time.time()
        self.done += amount
        speed = (amount/(now - self.last_tick ))
        print self.done, "/", self.total , "(%0.2f%%)"%(float(self.done)/float(self.total)*100)
        print "\t Elapsed:", self.show( now - self.start_time )
        print "\t Actual Speed:", "%0.7f items per second"%speed
        print "\t ETA:", self.show( (self.total-self.done)/speed)
        self.last_tick = now
        
    def show(self, seconds):
        hours = seconds / (60*60)
        minutes = (seconds%(60*60) ) / 60
        seconds_left = seconds % 60
        return "%02i:%02i:%02i"%(hours, minutes, seconds_left)
