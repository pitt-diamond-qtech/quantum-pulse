# Created on 1/31/20 by gurudev

from ftplib import FTP
HOST = '127.0.0.1'
PORT = 63217

ftp = FTP('')
ftp.connect(HOST,PORT)
ftp.login('user','12345')
ftp.retrlines('LIST')

# ftp.login()
# ftp.cwd('directory_name') #replace with your directory
# ftp.retrlines('LIST')

def uploadFile():
 filename = '0_1.wfm' #replace with your file in your home folder
 ftp.storbinary('STOR '+filename, open('./sequencefiles/'+filename, 'rb'))
 ftp.quit()

def downloadFile():
 filename = 'testfile.txt' #replace with your file in the directory ('directory_name')
 localfile = open(filename, 'wb')
 ftp.retrbinary('RETR ' + filename, localfile.write, 1024)
 ftp.quit()
 localfile.close()

uploadFile()
#downloadFile()