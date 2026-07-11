from NaukriAIBot.main import main


if __name__ == "__main__":
    main()

    except Exception:
        logger.exception("Automation failed.")

        if driver:
            screenshot = take_screenshot(driver, "error")

            logger.error(f"Failure screenshot : {screenshot}")

    finally:
        # Uncomment after testing
        # if driver:
        #     driver.quit()

        logger.info("========== Automation Finished ==========")


if __name__ == "__main__":
    main()
