import configparser
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

# コンフィグ
config = configparser.ConfigParser()
config.read('./conf/fx.conf')
FROM_ADDRESS = config['mail']['from_address']
TO_ADDRESS = config['mail']['to_address']
PASSWORD = config['mail']['password']


def send(subject, body):
    msg = MIMEText(body)
    msg['From'] = FROM_ADDRESS
    msg['To'] = TO_ADDRESS
    msg['Subject'] = subject
    msg['Date'] = formatdate()

    smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpobj.ehlo()
    smtpobj.starttls()
    smtpobj.ehlo()
    smtpobj.login(FROM_ADDRESS, PASSWORD)
    smtpobj.sendmail(FROM_ADDRESS, TO_ADDRESS, msg.as_string())
    smtpobj.close()
