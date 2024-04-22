#!/usr/bin/env python
import socket
import json
import sys

SHIPS_LP = {"frigate": 1, "destroyer": 2, "battleship": 3}


class BridgeDefense:
    def __init__(self, hostname, port1, gas):
        self._hostname = hostname
        self._port1 = port1
        self._gas = gas
        self._currentTurn = 0
        self._ships = []
        self._cannons = []

    def __del__(self):
        self._gameTerminationRequest()

    def _get_ip_address(self):
        """
        Obtém endereço a partir de um hostname (escolhe preferencialmente IPv6).
        """
        try:
            # Obtém informações de endereço(s) para esse hostname (usando UDP)
            addr_info = socket.getaddrinfo(
                self._hostname, self._port1, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP
            )

            # Itera sobre as informações
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_address = sockaddr[0]
                # Escolhe endereço IPv6 se estiver disponível
                if family == socket.AF_INET6:
                    return (ip_address, family)
            # Se não houver IPv6, escolhe IPv4
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_address = sockaddr[0]
                if family == socket.AF_INET:
                    return (ip_address, family)
        except socket.gaierror as e:
            print("Error:", e)
            sys.exit(0)

    def _serverCommunication(self, jsonRequest, serverNum):
        """
        Administra a comunicação com o servidor.

        Envia um JSON e recebe outro (se for mensagem de erro chama uma exceção e retorna None).

        Todos os métodos comunicantes com o servidor devem usá-lo.

        Obs.: O JSON informado deve estar no formato de string.
        """
        # Obtém endereço e família (IPv4 ou IPv6)
        ip_address, address_family = self._get_ip_address()

        # Tenta enviar a mensagem 5 vezes
        remaining_attempts = 5
        while remaining_attempts > 0:
            try:
                # Cria um socket UDP (e fecha a conexão automaticamente após as operações)
                with socket.socket(address_family, socket.SOCK_DGRAM) as client_socket:

                    # configura um timeout para não esperar indefinidamente
                    client_socket.settimeout(5)

                    # Transforma e envia a mensagem para o servidor (para a porta indicada nos parâmetros)
                    client_socket.sendto(
                        jsonRequest.encode(), (ip_address, self._port1 + serverNum)
                    )

                    # Recebe a resposta (com um tamanho máximo) e converte para JSON
                    response, _ = client_socket.recvfrom(1024)

                    # Decodifica os bits da resposta do servidor
                    response = response.decode()

                    # Verifica o tipo da mensagem para saber se é um game over ou não
                    dictResponse = json.loads(response)
                    if (
                        dictResponse["type"] == "gameover"
                        and dictResponse["status"] == 1
                    ):
                        print("JOGO ENCERRADO: " + dictResponse["description"])
                        # sys.exit(1)
                        return None
                    elif (
                        dictResponse["type"] == "gameover"
                        and dictResponse["status"] == 0
                    ):
                        print("JOGO ENCERRADO SEM NENHUM ERRO.")
                        # self._gameTerminationRequest()
                        return None

                    # Se tudo ocorrer bem, retorna o JSON da resposta
                    return response

            except socket.timeout:

                remaining_attempts -= 1

                if remaining_attempts == 0:
                    print(
                        "Não foi possíel se conectar com o servidor. Verifique sua conexão, o hostname e a porta."
                    )
                    return None
                else:
                    print(
                        f"Ocorreu um timeout ao tentar conexão com o servidor {serverNum}. Tentando novamente..."
                    )

            except socket.error as e:
                if remaining_attempts == 0:
                    print("Failure!")
                    return None
                print("An error occurred. Retrying... Socket error:", e)
                remaining_attempts -= 1

        # Se nenhum erro ocorrer, converte a resposta para JSON

    def _authenticationRequest(self):
        """
        Recebe um GAS, envia para o servidor, que retorna autenticação.
        """

        # Transforma os dados necessários para esse tipo de requisição em um JSON
        data = {"type": "authreq", "auth": self._gas}
        jsonMessage = json.dumps(data)

        # Faz a autenticação nos quatro servidores (rios)
        successfulAuthentication = True
        for i in range(0, 4):

            # Recebe a resposta do servidor e transforma em um dicionário
            jsonResponse = self._serverCommunication(jsonMessage, i)
            dictResponse = json.loads(jsonResponse)

            # Retorna o status da autenticação em cada servidor (rio)
            if dictResponse["status"] == 0:
                print(f"GAS autenticado no rio {i}")
                successfulAuthentication = successfulAuthentication < True
            else:
                print(f"Não foi possivel autenticar GAS no rio {i}")
                successfulAuthentication = successfulAuthentication < False
        # Retorna True somente se a autenticação for bem sucedida em todos os servidores
        return successfulAuthentication

    def _cannonPlacementRequest(self):
        data = {"type": "getcannons", "auth": self._gas}
        jsonMessage = json.dumps(data)

        # Todos os servidores respondem igualmente a requisição de canhões
        jsonResponse = self._serverCommunication(jsonMessage, 0)
        dictResponse = json.loads(jsonResponse)

        self._cannons = dictResponse["cannons"]

    def _turnStateRequest(self):
        # Esse método é chamado a cada novo turno para saber quanis navios apareceram na entrada do rio
        # Cada servidor controla um rio, então mandar requisição para os 4 servidores para reconstruir o estado do turno
        # Ideia: armazenar a posição e a vida dos navios na variável "__ships"

        # self._currentTurn += 1
        return

    def _shotMessage(self):
        shotResult = 1
        #  A partir das variáveis "__ships" e "__cannons", que representam o turno atual,
        #  desenvolver algoritmo para atirar nos navios possíveis
        #  a solução deve estar na documentação
        #  Obs.: Receber a confirmação do servidor antes de realmente decrementar a vida do navio
        return shotResult

    def _gameTerminationRequest(self):
        data = {"type": "quit", "auth": self._gas}
        jsonMessage = json.dumps(data)
        # Quit pode ser realizado em um servidor e todos encerrarão o jogo
        self._serverCommunication(jsonMessage, 0)

    def playGame(self):
        # Único método visível para fora da classe
        # Será usado para dar início ao jogo

        # ETAPA1: Faz a autenticação nos 4 rios (já implementado)
        print("--------- INICIANDO AUTENTICAÇÃO ---------")
        if not self._authenticationRequest():
            print(
                "Para continuar é preciso autenticar em todos os rios. Tente novamente."
            )
            sys.exit(0)

        print("\n--------- RECEBENDO OS CANHÕES ---------")
        self._cannonPlacementRequest()
        print(f"Canhões: {self._cannons}")

        while True:
            # ETAPA3: Avança um turno e reconstroi a posição dos navios (a implementar)
            # desenvolver método "_turnStateRequest()"
            print("\n--------- AVANÇA TURNO E POSICIONA OS NAVIOS ---------")
            self._turnStateRequest()

            # ETAPA4: Atira nos navios da melhor forma possível (a implementar)
            # desenvolver método "_shotMessage()"
            print("\n--------- ATIRANDO ---------")

            # Só pra facilitar no desenvolvimento
            if self._currentTurn == 0:
                break

        # ETAPA5: Repete as etapas 4 e 5 até o fim do jogo (a implementar)

        # ETAPA6: Retorna score
        return None


if __name__ == "__main__":
    # verifica se o número de argumentos é três
    num_args = len(sys.argv)
    if num_args != 4:
        print(
            "Parâmetros incorretos. Como usar: python client.py <hostname> <port 1> <GAS>"
        )
        sys.exit(1)

    # Obtém os argumentos a partir dos parâmetros do programa na linha de comando
    host = sys.argv[1]
    port = int(sys.argv[2])
    gas = sys.argv[3]

    # EXEMPLO DE PARÂMETROS VALIDOS PARA TESTE
    # host = "pugna.snes.dcc.ufmg.br"
    # port = 51111
    # gas = "202011111122:1234567890:afc97aecb06dec27ded0534a4ceaf6aacb8c0291abd304ea708fc459ed0ac8eb+202011111123:1234567899:b7a40be27a38fd979186b0f7eeb45b706a2da859bba03f699d8cbf67b43d412e+0c2dc10ca2d44af785ddb45ad39c572c3754dcef38b1dc38b044a1ef002eece6"

    newGame = BridgeDefense(host, port, gas)
    newGame.playGame()
