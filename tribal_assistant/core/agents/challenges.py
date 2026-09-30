"""How the agents pursue each achievement of the game, or why they leave it alone."""

from dataclasses import dataclass
from typing import Any, ClassVar

AUTO = "auto"
PASSIVE = "passive"
BLOCKED = "blocked"
SOCIAL = "social"


@dataclass(frozen=True)
class Pursuit:
    status: str
    agent: str
    how: str


class ChallengePlan:
    PLAN: ClassVar[dict[str, Pursuit]] = {
        "Arquiteto": Pursuit(AUTO, "infrastructure", "cada obra concluída conta; o coordenador mantém a fila de construção cheia"),
        "Campeão de pontuação": Pursuit(AUTO, "infrastructure", "pontos vêm das obras e do crescimento da aldeia"),
        "Líder em pontos": Pursuit(AUTO, "infrastructure", "longo prazo: crescer mais rápido que os vizinhos"),
        "Líder em pontos do continente": Pursuit(AUTO, "infrastructure", "longo prazo: crescer mais rápido que o continente"),
        "Coletor": Pursuit(AUTO, "attack", "coleta com as tropas paradas em todos os níveis livres"),
        "Coletor do dia": Pursuit(AUTO, "attack", "coleta contínua; o ranking diário é disputado com o mundo todo"),
        "Fora do tempo": Pursuit(AUTO, "free_finish", "finaliza de graça toda obra curta assim que o botão aparece"),
        "Unidade de recrutamento": Pursuit(AUTO, "recruitment", "recrutamento em lotes conforme o papel da aldeia"),
        "Ladrão": Pursuit(AUTO, "attack", "saques em aldeias bárbaras próximas"),
        "Saqueador": Pursuit(AUTO, "attack", "cada saque em bárbara conta"),
        "Saqueador de recursos do dia": Pursuit(AUTO, "attack", "saques contínuos; ranking diário do mundo"),
        "Saqueador de aldeias do dia": Pursuit(AUTO, "attack", "saques contínuos; ranking diário do mundo"),
        "Mestre das Missões": Pursuit(AUTO, "quartermaster", "conclui missões e coleta as recompensas"),
        "Nível do Paladino": Pursuit(AUTO, "steward", "treino do paladino por XP na estátua"),
        "Estudante talentoso": Pursuit(AUTO, "steward", "aprende habilidades do paladino quando há livro ou ponto livre"),
        "Comerciante Guru": Pursuit(AUTO, "economy", "trocas no mercado sempre que um recurso sobra"),
        "Antiga Forja: Colecionador de fórmulas": Pursuit(AUTO, "steward", "na forja, tenta primeiro combinações que ainda não estão no livro"),
        "Antiga Forja: Mestre Ferreiro": Pursuit(AUTO, "steward", "trabalha itens com os materiais grátis do evento"),
        "Conquista": Pursuit(AUTO, "expansion", "longo prazo: nobres para conquistar aldeias bárbaras"),
        "O Arqueólogo": Pursuit(PASSIVE, "steward", "relíquias chegam por eventos e recompensas; o mordomo equipa as novas"),
        "Pertence a um tesouro": Pursuit(PASSIVE, "steward", "relíquias chegam por eventos e recompensas"),
        "Fortuna e Glória": Pursuit(PASSIVE, "steward", "o mordomo equipa toda relíquia que chegar"),
        "Bibliotecário": Pursuit(PASSIVE, "steward", "livros de habilidade chegam por recompensas e ficam no inventário"),
        "Explorador": Pursuit(PASSIVE, "defense", "conta sozinho quando exploradores inimigos são barrados"),
        "Anos de serviço": Pursuit(PASSIVE, "", "só o tempo de jogo"),
        "Destruidor de muralhas": Pursuit(BLOCKED, "", "exige aríetes contra muralhas; só em bárbaras, depois da oficina"),
        "Vândalo": Pursuit(BLOCKED, "", "exige catapultas; só em bárbaras, depois da oficina"),
        "Você é um fusionador?": Pursuit(BLOCKED, "", "fundir 3 relíquias iguais reduz o total de relíquias; ainda não automatizado"),
        "Banda dos Irmãos": Pursuit(BLOCKED, "", "segundo paladino exige outra aldeia"),
        "Atacante do dia": Pursuit(BLOCKED, "", "exige atacar jogadores, o que os agentes nunca fazem"),
        "Comandante de guerra": Pursuit(BLOCKED, "", "exige atacar jogadores, o que os agentes nunca fazem"),
        "Maior poder do dia": Pursuit(BLOCKED, "", "exige conquistar aldeias de jogadores"),
        "A reserva da aldeia foi feita com sucesso": Pursuit(BLOCKED, "", "exige reservas de tribo e nobres"),
        "Cara de sorte": Pursuit(BLOCKED, "", "depende de conquista com lealdade exata"),
        "Cara sem sorte": Pursuit(BLOCKED, "", "depende de conquista falha"),
        "Líder": Pursuit(BLOCKED, "", "exige derrotar tropas de jogadores"),
        "Mestre do campo de batalha": Pursuit(BLOCKED, "", "exige destruir exércitos de jogadores"),
        "Fé da Nobreza": Pursuit(BLOCKED, "", "exige derrotar um nobre inimigo em defesa"),
        "Defensor do dia": Pursuit(BLOCKED, "", "depende de ser atacado"),
        "Apoiador do dia": Pursuit(BLOCKED, "", "exige apoiar outros jogadores em combate"),
        "Reforços": Pursuit(BLOCKED, "", "exige apoiar outros jogadores"),
        "Morte de um herói": Pursuit(BLOCKED, "", "exige perder tropas apoiando outros jogadores"),
        "Auto-ataque": Pursuit(BLOCKED, "", "perder tropas de propósito; nunca"),
        "Auto-conquista": Pursuit(BLOCKED, "", "conquistar a própria aldeia; nunca"),
        "Vítima": Pursuit(BLOCKED, "", "ser conquistado; nunca"),
        "Ressurreição": Pursuit(BLOCKED, "", "reiniciar a conta no mundo; nunca"),
        "Filantropo": Pursuit(BLOCKED, "", "exige gastar premium; nunca"),
        "Irmãos de guerra": Pursuit(AUTO, "diplomacy", "aceita convite ou se candidata à tribo mais forte da região e fica 30 dias"),
        "Graduado": Pursuit(AUTO, "diplomacy", "aceita o mentor recomendado pelo jogo e segue até graduar"),
        "Amigo fiel": Pursuit(AUTO, "social", "aceita pedidos de amizade e pede amizade a colegas de tribo e vizinhos ativos, no ritmo do knob"),
        "O mentor": Pursuit(BLOCKED, "", "ser mentor exige conta veterana"),
        "Recrutamento bem sucedido": Pursuit(BLOCKED, "", "exige convidar pessoas reais por e-mail"),
    }
    UNKNOWN: ClassVar[Pursuit] = Pursuit(PASSIVE, "", "ainda sem estratégia mapeada")

    @classmethod
    def pursuit(cls, name: str) -> Pursuit:
        return cls.PLAN.get(name, cls.UNKNOWN)

    @classmethod
    def enrich(cls, item: dict[str, Any]) -> dict[str, Any]:
        pursuit = cls.pursuit(item["name"])
        current, target = item.get("current"), item.get("target")
        ratio = (current or 0) / target if target else None
        return {**item, "status": pursuit.status, "agent": pursuit.agent, "how": pursuit.how, "ratio": ratio}

    @classmethod
    def closest(cls, items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
        open_items = [cls.enrich(i) for i in items if not i.get("done") and i.get("target")]
        pursued = [i for i in open_items if i["status"] in (AUTO, PASSIVE)]
        return sorted(pursued, key=lambda i: -(i["ratio"] or 0))[:limit]
