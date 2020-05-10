######## IN CONTAINER.PY AT LINE 228 ADD #############

   
        self.id = r('docker run -id --privileged --name $name --hostname $name --net=none $image').strip()
        self.pid = r("docker inspect -f '{{.State.Pid}}' $self.id").strip().strip(b"'")
        self.pid = self.pid.decode("utf-8")
        self.proc_path = '/proc/%s/ns/' % self.pid
        self.mnt_fd = open(self.proc_path + 'mnt')
        self.var_run = '/var/run/netns/' + self.name     

###### IN W4SP_WEBAPP.PY AT LINE 213 CHANGE ######

@app.route('/is_ips')
def is_ips():
    """quick check to see if suricata is running"""

    if psef(b'suricata'):
        return 'ok',200
    else:
        return 'error',404



