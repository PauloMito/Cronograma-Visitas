setTimeout(function () {
  const mensagens = document.getElementById("mensagens");

  if (mensagens && mensagens.textContent.trim() !== "") {
    mensagens.classList.add("messages-hidden");
  }
}, 3000);