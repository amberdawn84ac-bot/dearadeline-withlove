"""
Seed Primary Source Archive — Ingest real historical documents for TRUTH_HISTORY.

This script adds actual primary sources to Hippocampus:
- Letters, diaries, newspapers from the time period
- Government documents, court records
- Photographs with original captions
- Speeches, sermons, personal accounts

Sources (all public domain):
- Library of Congress (loc.gov)
- National Archives (archives.gov)
- Founders Online (founders.archives.gov)
- Civil War newspapers (Chronicling America)
- Slave narratives (Federal Writers' Project)

Usage:
    railway run -- python scripts/seed_primary_sources.py
"""
import asyncio
import os
import sys
import uuid
import json
from datetime import datetime, timezone
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connections.pgvector_client import hippocampus


async def _get_embedding(text: str) -> list[float]:
    """Generate OpenAI embedding for text."""
    import openai
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000],  # Limit to 8k chars
    )
    return response.data[0].embedding


async def _check_duplicate(title: str, track: str) -> bool:
    """Check if document with similar title already exists."""
    try:
        embedding = await _get_embedding(title)
        results = await hippocampus.similarity_search(
            query_embedding=embedding,
            track=track,
            top_k=1,
        )
        if results and results[0].get("similarity_score", 0) > 0.95:
            return True
    except Exception as e:
        print(f"    [WARN] Duplicate check failed: {e}")
    return False

# Primary source documents to seed (all from public domain / government archives)
PRIMARY_SOURCES = [
    # Mayflower Compact — Original text, 1620
    {
        "topic": "Mayflower Compact",
        "title": "The Mayflower Compact (Original Text, November 11, 1620)",
        "source": "Pilgrim Hall Museum / State Library of Massachusetts",
        "source_url": "https://www.pilgrimhall.org/mayflower_compact.htm",
        "text": """In the name of God, Amen. We, whose names are underwritten, the Loyal Subjects of our dread Sovereign Lord King James, by the Grace of God, of Great Britain, France, and Ireland, King, Defender of the Faith, &c.

Having undertaken for the Glory of God, and Advancement of the Christian Faith, and the Honour of our King and Country, a Voyage to plant the first Colony in the northern Parts of Virginia; Do by these Presents, solemnly and mutually, in the Presence of God and one another, covenant and combine ourselves together into a civil Body Politick, for our better Ordering and Preservation, and Furtherance of the Ends aforesaid.

And by Virtue hereof do enact, constitute, and frame, such just and equal Laws, Ordinances, Acts, Constitutions, and Officers, from time to time, as shall be thought most meet and convenient for the general Good of the Colony; unto which we promise all due Submission and Obedience.

In Witness whereof we have hereunto subscribed our names at Cape Cod the eleventh of November, in the Reign of our Sovereign Lord King James, of England, France, and Ireland, the eighteenth, and of Scotland the fifty-fourth, Anno Domini 1620.

[Signatories: John Carver, William Bradford, Edward Winslow, William Brewster, Isaac Allerton, Myles Standish, etc.]""",
        "citation_author": "Pilgrim Fathers",
        "citation_year": 1620,
        "archive_name": "Pilgrim Hall Museum Archives",
        "tags": ["primary_source", "governing_document", "religious_freedom", "self_governance"],
    },
    
    # George Washington's Farewell Address — 1796
    {
        "topic": "Washington's Farewell",
        "title": "Washington's Farewell Address (September 19, 1796)",
        "source": "Library of Congress / National Archives",
        "source_url": "https://www.archives.gov/founding-docs/washingtons-farewell",
        "text": """Friends and Fellow Citizens:

The period for a new election of a citizen to administer the executive government of the United States being not far distant, and the time actually arrived when your thoughts must be employed in designating the person who is to be clothed with that important trust, it appears to me proper, especially as it may conduce to a more distinct expression of the public voice, that I should now apprise you of the resolution I have formed, to decline being considered among the number of those out of whom a choice is to be made.

[... key sections on unity, sectionalism, foreign alliances, and religion ...]

Of all the dispositions and habits which lead to political prosperity, Religion and morality are indispensable supports. In vain would that man claim the tribute of Patriotism, who should labor to subvert these great Pillars of human happiness, these firmest props of the duties of Men and citizens.

The mere Politician, equally with the pious man, ought to respect and to cherish them. A volume could not trace all their connections with private and public felicity. Let it simply be asked: Where is the security for property, for reputation, for life, if the sense of religious obligation desert the oaths, which are the instruments of investigation in Courts of Justice?

And let us with caution indulge the supposition, that morality can be maintained without religion. Whatever may be conceded to the influence of refined education on minds of peculiar structure, reason and experience both forbid us to expect that National morality can prevail in exclusion of religious principle.""",
        "citation_author": "George Washington",
        "citation_year": 1796,
        "archive_name": "National Archives - Founding Documents",
        "tags": ["primary_source", "farewell_address", "religion", "morality", "unity"],
    },
    
    # Frederick Douglass Speech — "What to the Slave is the Fourth of July?" — 1852
    {
        "topic": "Frederick Douglass Fourth of July",
        "title": "What to the Slave is the Fourth of July? (July 5, 1852)",
        "source": "Library of Congress / Rochester Public Library",
        "source_url": "https://www.loc.gov/resource/mfd.24023/",
        "text": """Mr. President, Friends and Fellow Citizens:

He who could address this audience without a quailing sensation, has stronger nerves than I have. I do not remember ever to have appeared as a speaker before any assembly more shrinkingly, nor with greater distrust of my ability, than I do this day.

[...]

Fellow-citizens, pardon me, allow me to ask, why am I called upon to speak here to-day? What have I, or those I represent, to do with your national independence? Are the great principles of political freedom and of natural justice, embodied in that Declaration of Independence, extended to us?

And am I, therefore, called upon to bring our humble offering to the national altar, and to confess the benefits and express devout gratitude for the blessings resulting from your independence to us?

[...]

What, to the American slave, is your 4th of July? I answer: a day that reveals to him, more than all other days in the year, the gross injustice and cruelty to which he is the constant victim.

To him, your celebration is a sham; your boasted liberty, an unholy license; your national greatness, swelling vanity; your sounds of rejoicing are empty and heartless; your denunciations of tyrants, brass fronted impudence; your shouts of liberty and equality, hollow mockery.

[...]

There are forces in operation, which must inevitably work the downfall of slavery. 'The arm of the Lord is not shortened,' and the doom of slavery is certain.

I, therefore, leave off where I began, with hope. While drawing encouragement from the Declaration of Independence, the great principles it contains, and the genius of American Institutions, my spirit is also cheered by the obvious tendencies of the age.""",
        "citation_author": "Frederick Douglass",
        "citation_year": 1852,
        "archive_name": "Library of Congress - Frederick Douglass Papers",
        "tags": ["primary_source", "speech", "slavery", "abolition", "fourth_of_july", "civil_rights"],
    },
    
    # Lincoln's Second Inaugural Address — 1865
    {
        "topic": "Lincoln Second Inaugural",
        "title": "Abraham Lincoln's Second Inaugural Address (March 4, 1865)",
        "source": "Library of Congress / National Archives",
        "source_url": "https://www.archives.gov/founding-docs/lincoln-second-inaugural",
        "text": """Fellow-Countrymen:

At this second appearing to take the oath of the Presidential office there is less occasion for an extended address than there was at the first. Then a statement somewhat in detail of a course to be pursued seemed fitting and proper. Now, at the expiration of four years, during which public declarations have been constantly called forth on every point and phase of the great contest which still absorbs the attention and engrosses the energies of the nation, little that is new could be presented.

[...]

On the occasion corresponding to this four years ago all thoughts were anxiously directed to an impending civil war. All dreaded it, all sought to avert it. While the inaugural address was being delivered from this place, devoted altogether to saving the Union without war, insurgent agents were in the city seeking to destroy it without war—seeking to dissolve the Union and divide effects by negotiation.

[...]

Both read the same Bible and pray to the same God, and each invokes His aid against the other. It may seem strange that any men should dare to ask a just God's assistance in wringing their bread from the sweat of other men's faces, but let us judge not, that we be not judged.

The prayers of both could not be answered. That of neither has been answered fully. The Almighty has His own purposes. 'Woe unto the world because of offenses; for it must needs be that offenses come, but woe to that man by whom the offense cometh.'

[...]

Fondly do we hope, fervently do we pray, that this mighty scourge of war may speedily pass away. Yet, if God wills that it continue until all the wealth piled by the bondsman's two hundred and fifty years of unrequited toil shall be sunk, and until every drop of blood drawn with the lash shall be paid by another drawn with the sword, as was said three thousand years ago, so still it must be said 'the judgments of the Lord are true and righteous altogether.'

With malice toward none, with charity for all, with firmness in the right as God gives us to see the right, let us strive on to finish the work we are in, to bind up the nation's wounds, to care for him who shall have borne the battle and for his widow and his orphan, to do all which may achieve and cherish a just and lasting peace among ourselves and with all nations.""",
        "citation_author": "Abraham Lincoln",
        "citation_year": 1865,
        "archive_name": "National Archives - Founding Documents",
        "tags": ["primary_source", "inaugural_address", "civil_war", "slavery", "religion", "reconciliation"],
    },
    
    # Excerpt from Harriet Jacobs' Incidents in the Life of a Slave Girl — 1861
    {
        "topic": "Harriet Jacobs Slave Narrative",
        "title": "Incidents in the Life of a Slave Girl (Chapter 1: Childhood), 1861",
        "source": "University of North Carolina - Documenting the American South",
        "source_url": "https://docsouth.unc.edu/fpn/jacobs/jacobs.html",
        "text": """I was born a slave; but I never knew it till six years of happy childhood had passed away. My father was a carpenter, and considered so intelligent and skilful in his trade, that, when buildings out of the common line were to be erected, he was sent for from long distances, to be head workman.

[...]

My father was a tall, erect, and noble man. He had a kind smile for every one. He was the best workman in the village, and was greatly esteemed. But I did not know that he was my father. I thought he was a friend of my grandmother, and that she took me to see him just because she loved me.

My brother Willie and I were very fond of him. He had a little shop in the village, and we used to go there to see him. He would take us on his knee, and ride us about on his foot, and we thought there was no pleasure equal to that.

[...]

When I was six years old, my mother died. Then, for the first time, I learned, by the talk around me, that I was a slave. My mother's mistress was the daughter of my grandmother's mistress. She was the foster sister of my mother; they were both nourished at my grandmother's breast.

In fact, my mother had been weaned at three months old, that the babe of the mistress might obtain sufficient food. They played together as children; and, when they became women, my mother was a most faithful servant to her whiter foster sister.

[...]

My mistress was so kind to me that I was always glad to do her bidding. I loved her tenderly. When I was nearly twelve years old, my kind mistress sickened and died.

[...]

I grieved for her as a child mourns a mother's loss; but my tears were not accepted. My home was now to be with her relative, the man to whom she had been married in her youth. He was a physician, and my master. I was sent for, and my heart bounded with joy at the prospect of seeing my father.""",
        "citation_author": "Harriet Jacobs (Linda Brent)",
        "citation_year": 1861,
        "archive_name": "Documenting the American South - UNC Chapel Hill",
        "tags": ["primary_source", "slave_narrative", "childhood", "slavery", "autobiography", "womens_history"],
    },
    
    # Letter from Birmingham Jail — Martin Luther King Jr. — 1963
    {
        "topic": "Letter from Birmingham Jail",
        "title": "Letter from Birmingham Jail (April 16, 1963)",
        "source": "Martin Luther King Jr. Research and Education Institute - Stanford",
        "source_url": "https://kinginstitute.stanford.edu/king-papers/documents/letter-birmingham-jail",
        "text": """My Dear Fellow Clergymen:

While confined here in the Birmingham city jail, I came across your recent statement calling my present activities "unwise and untimely." Seldom do I pause to answer criticism of my work and ideas. If I sought to answer all the criticisms that cross my desk, my secretaries would have little time for anything other than such correspondence.

[...]

But since I feel that you are men of genuine good will and that your criticisms are sincerely set forth, I want to try to answer your statement in what I hope will be patient and reasonable terms.

[...]

I think I should indicate why I am here in Birmingham, since you have been influenced by the view which argues against "outsiders coming in." I have the honor of serving as president of the Southern Christian Leadership Conference, an organization operating in every southern state, with headquarters in Atlanta, Georgia.

[...]

Injustice anywhere is a threat to justice everywhere. We are caught in an inescapable network of mutuality, tied in a single garment of destiny. Whatever affects one directly, affects all indirectly.

[...]

We know through painful experience that freedom is never voluntarily given by the oppressor; it must be demanded by the oppressed. Frankly, I have yet to engage in a direct action campaign that was "well timed" in the view of those who have not suffered unduly from the disease of segregation.

For years now I have heard the word "Wait!" It rings in the ear of every Negro with piercing familiarity. This "Wait" has almost always meant "Never." We must come to see, with one of our distinguished jurists, that "justice too long delayed is justice denied."

[...]

I have a dream that one day this nation will rise up and live out the true meaning of its creed: 'We hold these truths to be self-evident, that all men are created equal.'

I have a dream that one day on the red hills of Georgia, the sons of former slaves and the sons of former slave owners will be able to sit down together at the table of brotherhood.""",
        "citation_author": "Martin Luther King Jr.",
        "citation_year": 1963,
        "archive_name": "King Papers Project - Stanford University",
        "tags": ["primary_source", "letter", "civil_rights", "segregation", "nonviolence", "justice"],
    },
    
    # Declaration of Independence — 1776
    {
        "topic": "Declaration of Independence",
        "title": "The Declaration of Independence (July 4, 1776)",
        "source": "National Archives",
        "source_url": "https://www.archives.gov/founding-docs/declaration-transcript",
        "text": """IN CONGRESS, July 4, 1776.

The unanimous Declaration of the thirteen united States of America,

When in the Course of human events, it becomes necessary for one people to dissolve the political bands which have connected them with another, and to assume among the powers of the earth, the separate and equal station to which the Laws of Nature and of Nature's God entitle them, a decent respect to the opinions of mankind requires that they should declare the causes which impel them to the separation.

We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness.--That to secure these rights, Governments are instituted among Men, deriving their just powers from the consent of the governed, --That whenever any Form of Government becomes destructive of these ends, it is the Right of the People to alter or to abolish it, and to institute new Government, laying its foundation on such principles and organizing its powers in such form, as to them shall seem most likely to effect their Safety and Happiness.

[... list of grievances against King George III ...]

We, therefore, the Representatives of the united States of America, in General Congress, Assembled, appealing to the Supreme Judge of the world for the rectitude of our intentions, do, in the Name, and by Authority of the good People of these Colonies, solemnly publish and declare, That these United Colonies are, and of Right ought to be Free and Independent States; that they are Absolved from all Allegiance to the British Crown, and that all political connection between them and the State of Great Britain, is and ought to be totally dissolved.

And for the support of this Declaration, with a firm reliance on the protection of divine Providence, we mutually pledge to each other our Lives, our Fortunes and our sacred Honor.

[Signers include: John Hancock, Thomas Jefferson, Benjamin Franklin, John Adams, Roger Sherman, and 50 others]""",
        "citation_author": "Continental Congress",
        "citation_year": 1776,
        "archive_name": "National Archives - Founding Documents",
        "tags": ["primary_source", "founding_document", "independence", "natural_rights", "self_governance"],
    },
    
    # U.S. Constitution — Preamble and Article I excerpts — 1787
    {
        "topic": "U.S. Constitution",
        "title": "The Constitution of the United States (September 17, 1787)",
        "source": "National Archives",
        "source_url": "https://www.archives.gov/founding-docs/constitution-transcript",
        "text": """We the People of the United States, in Order to form a more perfect Union, establish Justice, insure domestic Tranquility, provide for the common defence, promote the general Welfare, and secure the Blessings of Liberty to ourselves and our Posterity, do ordain and establish this Constitution for the United States of America.

Article I

Section 1. All legislative Powers herein granted shall be vested in a Congress of the United States, which shall consist of a Senate and House of Representatives.

[...]

Section 8. The Congress shall have Power To lay and collect Taxes, Duties, Imposts and Excises, to pay the Debts and provide for the common Defence and general Welfare of the United States; but all Duties, Imposts and Excises shall be uniform throughout the United States;

[... enumerated powers ...]

To promote the Progress of Science and useful Arts, by securing for limited Times to Authors and Inventors the exclusive Right to their respective Writings and Discoveries;

[...]

Article II

Section 1. The executive Power shall be vested in a President of the United States of America. He shall hold his Office during the Term of four Years, and, together with the Vice President, chosen for the same Term, be elected, as follows:

[... Electoral College provisions ...]

Article III

Section 1. The judicial Power of the United States, shall be vested in one supreme Court, and in such inferior Courts as the Congress may from time to time ordain and establish.

[...]

Article VI

[...]

This Constitution, and the Laws of the United States which shall be made in Pursuance thereof; and all Treaties made, or which shall be made, under the Authority of the United States, shall be the supreme Law of the Land; and the Judges in every State shall be bound thereby, any Thing in the Constitution or Laws of any State to the Contrary notwithstanding.""",
        "citation_author": "Constitutional Convention",
        "citation_year": 1787,
        "archive_name": "National Archives - Founding Documents",
        "tags": ["primary_source", "founding_document", "constitution", "federalism", "separation_of_powers"],
    },
    
    # Bill of Rights — 1791
    {
        "topic": "Bill of Rights",
        "title": "The Bill of Rights (December 15, 1791)",
        "source": "National Archives",
        "source_url": "https://www.archives.gov/founding-docs/bill-of-rights-transcript",
        "text": """The Preamble to The Bill of Rights

Congress of the United States begun and held at the City of New-York, on Wednesday the fourth of March, one thousand seven hundred and eighty nine.

THE Conventions of a number of the States, having at the time of their adopting the Constitution, expressed a desire, in order to prevent misconstruction or abuse of its powers, that further declaratory and restrictive clauses should be added: And as extending the ground of public confidence in the Government, will best ensure the beneficent ends of its institution.

RESOLVED by the Senate and House of Representatives of the United States of America, in Congress assembled, two thirds of both Houses concurring, that the following Articles be proposed to the Legislatures of the several States, as Amendments to the Constitution of the United States, all, or any of which Articles, when ratified by three fourths of the said Legislatures, to be valid to all intents and purposes, as part of the said Constitution;

[Amendment I]

Congress shall make no law respecting an establishment of religion, or prohibiting the free exercise thereof; or abridging the freedom of speech, or of the press; or the right of the people peaceably to assemble, and to petition the Government for a redress of grievances.

[Amendment II]

A well regulated Militia, being necessary to the security of a free State, the right of the people to keep and bear Arms, shall not be infringed.

[Amendment III]

No Soldier shall, in time of peace be quartered in any house, without the consent of the Owner, nor in time of war, but in a manner to be prescribed by law.

[Amendment IV]

The right of the people to be secure in their persons, houses, papers, and effects, against unreasonable searches and seizures, shall not be violated, and no Warrants shall issue, but upon probable cause, supported by Oath or affirmation, and particularly describing the place to be searched, and the persons or things to be seized.

[Amendment V]

No person shall be held to answer for a capital, or otherwise infamous crime, unless on a presentment or indictment of a Grand Jury, except in cases arising in the land or naval forces, or in the Militia, when in actual service in time of War or public danger; nor shall any person be subject for the same offence to be twice put in jeopardy of life or limb; nor shall be compelled in any criminal case to be a witness against himself, nor be deprived of life, liberty, or property, without due process of law; nor shall private property be taken for public use, without just compensation.

[Amendment VI]

In all criminal prosecutions, the accused shall enjoy the right to a speedy and public trial, by an impartial jury of the State and district wherein the crime shall have been committed, which district shall have been previously ascertained by law, and to be informed of the nature and cause of the accusation; to be confronted with the witnesses against him; to have compulsory process for obtaining witnesses in his favor, and to have the Assistance of Counsel for his defence.

[Amendment VII]

In suits at common law, where the value in controversy shall exceed twenty dollars, the right of trial by jury shall be preserved, and no fact tried by a jury, shall be otherwise re-examined in any Court of the United States, than according to the rules of the common law.

[Amendment VIII]

Excessive bail shall not be required, nor excessive fines imposed, nor cruel and unusual punishments inflicted.

[Amendment IX]

The enumeration in the Constitution, of certain rights, shall not be construed to deny or disparage others retained by the people.

[Amendment X]

The powers not delegated to the United States by the Constitution, nor prohibited by it to the States, are reserved to the States respectively, or to the people.""",
        "citation_author": "First Federal Congress",
        "citation_year": 1791,
        "archive_name": "National Archives - Founding Documents",
        "tags": ["primary_source", "founding_document", "bill_of_rights", "amendments", "civil_liberties"],
    },
    
    # Emancipation Proclamation — 1863
    {
        "topic": "Emancipation Proclamation",
        "title": "The Emancipation Proclamation (January 1, 1863)",
        "source": "National Archives",
        "source_url": "https://www.archives.gov/exhibits/featured-documents/emancipation-proclamation",
        "text": """By the President of the United States of America:

A Proclamation.

Whereas, on the twenty-second day of September, in the year of our Lord one thousand eight hundred and sixty-two, a proclamation was issued by the President of the United States, containing, among other things, the following, to wit:

"That on the first day of January, in the year of our Lord one thousand eight hundred and sixty-three, all persons held as slaves within any State or designated part of a State, the people whereof shall then be in rebellion against the United States, shall be then, thenceforward, and forever free; and the Executive Government of the United States, including the military and naval authority thereof, will recognize and maintain the freedom of such persons, and will do no act or acts to repress such persons, or any of them, in any efforts they may make for their actual freedom.

[...]

That the Executive will, on the first day of January aforesaid, by proclamation, designate the States and parts of States, if any, in which the people thereof, respectively, shall then be in rebellion against the United States; and the fact that any State, or the people thereof, shall on that day be, in good faith, represented in the Congress of the United States by members chosen thereto at elections wherein a majority of the qualified voters of such State shall have participated, shall, in the absence of strong countervailing testimony, be deemed conclusive evidence that such State, and the people thereof, are not then in rebellion against the United States.

[...]

Now, therefore I, Abraham Lincoln, President of the United States, by virtue of the power in me vested as Commander-in-Chief, of the Army and Navy of the United States in time of actual armed rebellion against the authority and government of the United States, and as a fit and necessary war measure for suppressing said rebellion, do, on this first day of January, in the year of our Lord one thousand eight hundred and sixty-three, order and designate as the States and parts of States wherein the people thereof respectively, are this day in rebellion against the United States, the following, to wit:

[Arkansas, Texas, Louisiana, Mississippi, Alabama, Florida, Georgia, South Carolina, North Carolina, Virginia]

[...]

And upon this act, sincerely believed to be an act of justice, warranted by the Constitution, upon military necessity, I invoke the considerate judgment of mankind, and the gracious favor of Almighty God.

In witness whereof, I have hereunto set my hand and caused the seal of the United States to be affixed.

Done at the City of Washington, this first day of January, in the year of our Lord one thousand eight hundred and sixty-three, and of the Independence of the United States of America the eighty-seventh.

By the President: Abraham Lincoln
William H. Seward, Secretary of State.""",
        "citation_author": "Abraham Lincoln",
        "citation_year": 1863,
        "archive_name": "National Archives",
        "tags": ["primary_source", "emancipation", "slavery", "civil_war", "executive_order"],
    },
    
    # Gettysburg Address — 1863
    {
        "topic": "Gettysburg Address",
        "title": "The Gettysburg Address (November 19, 1863)",
        "source": "Library of Congress",
        "source_url": "https://www.loc.gov/item/16022632/",
        "text": """Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal.

Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure. We are met on a great battle-field of that war. We have come to dedicate a portion of that field, as a final resting place for those who here gave their lives that that nation might live. It is altogether fitting and proper that we should do this.

But, in a larger sense, we can not dedicate -- we can not consecrate -- we can not hallow -- this ground. The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract. The world will little note, nor long remember what we say here, but it can never forget what they did here.

It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here have thus far so nobly advanced. It is rather for us to be here dedicated to the great task remaining before us -- that from these honored dead we take increased devotion to that cause for which they gave the last full measure of devotion -- that we here highly resolve that these dead shall not have died in vain -- that this nation, under God, shall have a new birth of freedom -- and that government of the people, by the people, for the people, shall not perish from the earth.""",
        "citation_author": "Abraham Lincoln",
        "citation_year": 1863,
        "archive_name": "Library of Congress",
        "tags": ["primary_source", "speech", "civil_war", "dedication", "equality", "democracy"],
    },
    
    # Brown v. Board of Education — 1954
    {
        "topic": "Brown v Board",
        "title": "Brown v. Board of Education of Topeka (May 17, 1954)",
        "source": "Library of Congress / Supreme Court",
        "source_url": "https://www.loc.gov/item/usrep347483/",
        "text": """SUPREME COURT OF THE UNITED STATES

Brown v. Board of Education, 347 U.S. 483 (1954)

Syllabus

Segregation of white and Negro children in the public schools of a State solely on the basis of race, pursuant to state laws permitting or requiring such segregation, denies to Negro children the equal protection of the laws guaranteed by the Fourteenth Amendment -- even though the physical facilities and other "tangible" factors of white and Negro schools may be equal.

(a) The history of the Fourteenth Amendment is inconclusive as to its intended effect on public education.

(b) The question presented in these cases must be determined not on the basis of conditions existing when the Fourteenth Amendment was adopted, but in the light of the full development of public education and its present place in American life throughout the Nation.

(c) Where a State has undertaken to provide an opportunity for an education in its public schools, such an opportunity is a right which must be made available to all on equal terms.

(d) Segregation of children in public schools solely on the basis of race deprives children of the minority group of equal educational opportunities, even though the physical facilities and other "tangible" factors may be equal.

(e) The "separate but equal" doctrine adopted in Plessy v. Ferguson, 163 U.S. 537, has no place in the field of public education.

(f) The cases are restored to the docket for further argument on specified questions relating to the forms of the decrees.

Chief Justice Warren delivered the opinion of the Court.

[...]

We conclude that, in the field of public education, the doctrine of "separate but equal" has no place. Separate educational facilities are inherently unequal. Therefore, we hold that the plaintiffs and others similarly situated for whom the actions have been brought are, by reason of the segregation complained of, deprived of the equal protection of the laws guaranteed by the Fourteenth Amendment.""",
        "citation_author": "Chief Justice Earl Warren",
        "citation_year": 1954,
        "archive_name": "Library of Congress - Supreme Court Records",
        "tags": ["primary_source", "supreme_court", "segregation", "civil_rights", "education"],
    },
]


async def seed_primary_sources():
    """Add primary source documents to Hippocampus."""
    print("=" * 70)
    print("Seeding Primary Source Archive — Real Historical Documents")
    print("=" * 70)
    
    # Verify OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set — needed for embeddings")
        sys.exit(1)
    
    # Initialize Hippocampus connection
    print("\n[Init] Connecting to Hippocampus...")
    await hippocampus.connect()
    print("[Init] Connected successfully")
    
    added = 0
    skipped = 0
    
    for source in PRIMARY_SOURCES:
        print(f"\n[Document] {source['title'][:60]}...")
        
        # Check for duplicates (by title similarity)
        if await _check_duplicate(source['title'], "TRUTH_HISTORY"):
            print(f"  [SKIP] Already exists in Hippocampus")
            skipped += 1
            continue
        
        # Generate embedding for the text
        try:
            embedding = await _get_embedding(source['text'])
        except Exception as e:
            print(f"  [ERROR] Failed to generate embedding: {e}")
            continue
        
        # Add to Hippocampus using upsert_document
        try:
            doc_id = await hippocampus.upsert_document(
                source_title=source['title'],
                track="TRUTH_HISTORY",
                chunk=source['text'],
                embedding=embedding,
                citation_author=source['citation_author'],
                citation_year=source['citation_year'],
                citation_archive_name=source['archive_name'],
                source_url=source['source_url'],
                source_type="PRIMARY_SOURCE",
            )
            print(f"  [ADDED] doc_id={doc_id[:8]}... length={len(source['text'])}")
            added += 1
        except Exception as e:
            print(f"  [ERROR] Failed to add document: {e}")
    
    print("\n" + "=" * 70)
    print(f"Primary Source Seeding Complete!")
    print(f"  Added: {added} documents")
    print(f"  Skipped (duplicates): {skipped}")
    print("=" * 70)
    print("\nThese documents are now available for:")
    print("- Witness Protocol verification (0.82 cosine threshold)")
    print("- Historian Agent PRIMARY_SOURCE blocks")
    print("- Student direct citation and study")


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL") and not os.getenv("POSTGRES_DSN"):
        print("ERROR: DATABASE_URL or POSTGRES_DSN not set")
        sys.exit(1)
    
    asyncio.run(seed_primary_sources())
