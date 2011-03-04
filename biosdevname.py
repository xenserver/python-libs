#!/usr/bin/python

import subprocess

class BiosDevName(object):

    def __init__(self):

        self.stdout = None
        self.stderr = None
        self.devices = []    

    def run(self, policy = "physical"):
        """run biosdevname -d on the commandline
        return boolean representing success/failure"""

        proc = subprocess.Popen(["/sbin/biosdevname", "-d",
                                 "--policy", policy],
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE)

        self.stdout, self.stderr = proc.communicate()


        if len(self.stderr):
            return False

        self.devices = []


        devices = [ x.strip() for x in self.stdout.split("\n\n") if len(x)]

        for d in devices:
            dinfo = {}
        
            for l in d.split("\n"):

                k, v = l.split(":", 1)
            
                dinfo[k.strip()] = v.strip()

            self.devices.append(dinfo)

        return True

    def eth_name(self, eth):
        return (subprocess.Popen(["/sbin/biosdevname", "-i", eth,
                                  "--policy", "all_ethN"],
                                 stdout = subprocess.PIPE).communicate())[0]
