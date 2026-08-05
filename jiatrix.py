from brain import ask

while True:
    user = input("[+] user: ")
    if user.lower().strip() not in ["exit", "die", "goodbye", "off", "terminal"]:
        ask(user)
        print("#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+#+ +#+")
    else:
        break