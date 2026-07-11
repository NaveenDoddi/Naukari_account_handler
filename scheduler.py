import schedule
import time
from update_resume import main

schedule.every().day.at("09:00").do(main)

print("Scheduler started...")

while True:
    schedule.run_pending()
    time.sleep(30)