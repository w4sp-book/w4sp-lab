######## IN CONTAINER.PY AT LINE 228 ADD #############

   
        self.id = r('docker run -id --privileged --name $name --hostname $name --net=none $image').strip()
        self.pid = r("docker inspect -f '{{.State.Pid}}' $self.id").strip().strip(b"'")
        self.pid = self.pid.decode("utf-8")
        self.proc_path = '/proc/%s/ns/' % self.pid
        self.mnt_fd = open(self.proc_path + 'mnt')
        self.var_run = '/var/run/netns/' + self.name     

###### IN W4SP_WEBAPP.PY AT LINE 224 CHANGE ######


@app.route('/ips')
def ips():
    """this starts suricata if it isn't running"""

    if psef('suricata'):
        return 'error',404

    #if sw2 isn't even up then we need to bail
    if not w4sp.c('sw2'):
        return 'error',404
